#!/usr/bin/env bash
# Task 05 acceptance assertion 2, first half: does this plain-Docker topology form the
# boundary "the workload reaches only the proxy, and only the proxy has outbound access"?
# Not product code: it measures the container/network topology, it does not serve the app.
#
# Run it from the repository root (or anywhere -- every path below is derived from this
# file's location, except the evidence directory, which defaults to $PWD/.tmp/t05-topology):
#
#   bash apps/backend/tests/providers/runtime/topology-probe.sh
#   NEGATIVE_CONTROL=1 bash apps/backend/tests/providers/runtime/topology-probe.sh
#
# Exit code 0 with "status=verified" means every assertion below was measured and held.
# NEGATIVE_CONTROL=1 deliberately joins the workload to the egress network: the negative
# assertions must then fail, which is a self-test of the harness, never a topology result.
#
# This half is Harbor-independent. Passing it does NOT mean acceptance passed: the fixed
# Harbor still has to allow the same topology (T2, on the owner's machine).
set -uo pipefail
# Git Bash rewrites container-side absolute paths and /dev/tcp arguments into Windows paths,
# which silently breaks the probe and yields false-negative CLOSED results.
export MSYS_NO_PATHCONV=1

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tests/providers/runtime/topology-lib.sh
. "${HERE}/topology-lib.sh"
. "${HERE}/topology-verdicts.sh"

# --- configuration ----------------------------------------------------------------------
SUFFIX=""
[ "${NEGATIVE_CONTROL:-0}" = "1" ] && SUFFIX="-negative-control"

SCOPE="t05-topology-$(date +%Y%m%d-%H%M%S)"
LABEL_TASK="agentexam.task=05"
LABEL_SCOPE="agentexam.scope=${SCOPE}"
NAME="agentexam-t05-topology"
EVIDENCE_DIR="${T05_EVIDENCE_DIR:-${PWD}/.tmp/t05-topology}"
mkdir -p "${EVIDENCE_DIR}"
TRANSCRIPT="${EVIDENCE_DIR}/transcript${SUFFIX}.txt"
DIAG="${EVIDENCE_DIR}/harness-failure${SUFFIX}.txt"

WORKLOAD="${NAME}-workload-1"
PROXY="${NAME}-proxy-1"
UPSTREAM="${NAME}-fakeupstream-1"
OTHER="${NAME}-othertrial-1"

# Overridable so a machine that already has other images cached does not have to pull
# these two: the probe needs any image with bash and /dev/tcp, and any image that can listen
# on a TCP port (the listener is driven through its own redis-cli).
WORKLOAD_IMAGE="${T05_WORKLOAD_IMAGE:-debian:bookworm-slim}"
LISTENER_IMAGE="${T05_LISTENER_IMAGE:-redis:7-alpine}"
ENTRY_PORT=6379          # the proxy's fixed entry the workload may reach
RELAY_PORT=8080          # minimal forwarding stand-in, for the positive control only
# Resolved from the image at setup rather than hardcoded: the tmpfs must be owned by whoever
# the listener runs as, and that id can differ between image variants.
REDIS_UID=""
REDIS_GID=""
MARKER="agentexam-proxy-marker"
# The marker is the relay script's own path: redis rewrites its process title, so a redis
# argv would never be found. Bracketed so the scanning shell cannot match itself.
RELAY_SCRIPT="/tmp/agentexam-proxy-marker-relay.sh"
MARKER_RE="agentexam-proxy-marke[r]-relay.sh"
SECRET_HOST="${T05_FAKE_PROVIDER_FILE:-${HERE}/fake-provider.json}"
SECRET_IN_PROXY="/run/agentexam-private/provider.json"
SENTINEL="FAKE-T05-SENTINEL"

INT="${NAME}_internal"
EGR="${NAME}_egress"
OTH="${NAME}_other"

COMMON=(--label "${LABEL_TASK}" --label "${LABEL_SCOPE}"
  --cap-drop ALL --security-opt no-new-privileges)
NETS=(--label "${LABEL_TASK}" --label "${LABEL_SCOPE}")

: > "${TRANSCRIPT}"
trap t05_cleanup EXIT

# --- setup ------------------------------------------------------------------------------
echo "== setup =="
t05_cleanup
listener_ids="$(docker run --rm --entrypoint id "${LISTENER_IMAGE}" redis 2>/dev/null)"
REDIS_UID="$(printf '%s' "${listener_ids}" | sed -n 's/.*uid=\([0-9][0-9]*\).*/\1/p')"
REDIS_GID="$(printf '%s' "${listener_ids}" | sed -n 's/.*gid=\([0-9][0-9]*\).*/\1/p')"
# Listeners run as the image's redis user so the official entrypoint skips its privilege
# drop: with --cap-drop ALL that step fails ("setpriv: setresuid failed", exit 127) and the
# container dies before it can listen. --cap-drop ALL itself is kept on every container.
LISTENER=(--user redis "--tmpfs" "/data:uid=${REDIS_UID},gid=${REDIS_GID}")
docker network create --internal "${NETS[@]}" "${INT}" >/dev/null
docker network create "${NETS[@]}" "${EGR}" >/dev/null
docker network create --internal "${NETS[@]}" "${OTH}" >/dev/null

docker run -d --name "${WORKLOAD}" "${COMMON[@]}" \
  --network "${INT}" "${WORKLOAD_IMAGE}" sleep 600 >/dev/null
if [ -n "${SUFFIX}" ]; then
  docker network connect "${EGR}" "${WORKLOAD}" >/dev/null   # the deliberate leak
fi
PROXY_CMD='redis-server --port '"${ENTRY_PORT}"' --save "" --appendonly no \
--dbfilename '"${MARKER}"'.rdb --loglevel warning & \
printf "#!/bin/sh\nexec nc '"${UPSTREAM}"' '"${ENTRY_PORT}"'\n" > '"${RELAY_SCRIPT}"'; \
chmod +x '"${RELAY_SCRIPT}"'; nc -lk -p '"${RELAY_PORT}"' -e '"${RELAY_SCRIPT}"''
docker run -d --name "${PROXY}" "${COMMON[@]}" "${LISTENER[@]}" \
  -v "${SECRET_HOST}:${SECRET_IN_PROXY}:ro" \
  --network "${INT}" --entrypoint sh "${LISTENER_IMAGE}" -c "${PROXY_CMD}" >/dev/null
docker network connect "${EGR}" "${PROXY}" >/dev/null
docker run -d --name "${UPSTREAM}" "${COMMON[@]}" "${LISTENER[@]}" \
  --network "${EGR}" "${LISTENER_IMAGE}" redis-server --save "" --loglevel verbose >/dev/null
docker run -d --name "${OTHER}" "${COMMON[@]}" "${LISTENER[@]}" \
  --network "${OTH}" "${LISTENER_IMAGE}" >/dev/null
sleep 4

PROXY_IP="$(t05_net_ip "${PROXY}" "${INT}")"
OTHER_IP="$(t05_net_ip "${OTHER}" "${OTH}")"
UPSTREAM_IP="$(t05_net_ip "${UPSTREAM}" "${EGR}")"
PROXY_EGRESS_IP="$(t05_net_ip "${PROXY}" "${EGR}")"
t05_health_gate || exit 2

# --- assertions -------------------------------------------------------------------------
GATEWAY="$(docker network inspect -f '{{(index .IPAM.Config 0).Gateway}}' "${INT}")"
echo "== assertions =="
t05_record 0 "mode" "${SUFFIX:-normal (no deliberate leak)}"
t05_record 0 "net ${INT} (internal)" "workload, proxy"
t05_record 0 "net ${EGR} (egress)" "proxy ${PROXY_EGRESS_IP}, upstream ${UPSTREAM_IP}"
t05_record 0 "net ${OTH} (internal)" "other-trial ${OTHER_IP}"

t05_record 1 "workload -> proxy entry ${PROXY_IP}:${ENTRY_PORT}" "$(t05_touch_probe "${WORKLOAD}" "${PROXY}" "${ENTRY_PORT}")"
t05_record 1 "  ping reply byte" "$(t05_ping_probe "${WORKLOAD}" "${PROXY}" "${ENTRY_PORT}")"
t05_record 2 "workload -> public 1.1.1.1:443" "$(t05_touch_probe "${WORKLOAD}" 1.1.1.1 443)"
t05_record 2 "workload -> public 223.5.5.5:53" "$(t05_touch_probe "${WORKLOAD}" 223.5.5.5 53)"
t05_record 3 "workload -> host gateway ${GATEWAY}:80" "$(t05_touch_probe "${WORKLOAD}" "${GATEWAY}" 80)"
t05_record 3 "workload -> metadata 169.254.169.254:80" "$(t05_touch_probe "${WORKLOAD}" 169.254.169.254 80)"
t05_record 3 "workload -> other trial ${OTHER_IP}:${ENTRY_PORT}" "$(t05_touch_probe "${WORKLOAD}" "${OTHER_IP}" "${ENTRY_PORT}")"
t05_record 3 "workload -> fake upstream ${UPSTREAM_IP}:${ENTRY_PORT}" "$(t05_touch_probe "${WORKLOAD}" "${UPSTREAM_IP}" "${ENTRY_PORT}")"
t05_record 4 "proxy -> fake upstream ${UPSTREAM_IP}:${ENTRY_PORT}" "$(t05_redis_ping "${PROXY}" "${UPSTREAM_IP}" "${ENTRY_PORT}")"

t05_record 5 "workload mounts" "$(docker inspect -f '{{json .Mounts}}' "${WORKLOAD}")"
t05_record 5 "proxy mounts" "$(docker inspect -f '{{json .Mounts}}' "${PROXY}")"
# Docker versions render an empty binding map differently ({} or null), so the verdict counts
# the marker a real published port always carries instead of matching one rendering.
t05_record 5 "published port bindings (all four)" \
  "$(docker inspect -f '{{.Name}} {{json .HostConfig.PortBindings}}' "${WORKLOAD}" "${PROXY}" "${UPSTREAM}" "${OTHER}" | tr '\n' ' ')"
t05_record 5 "docker.sock mount sources (proxy)" \
  "$(docker inspect -f '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' "${PROXY}" | grep -c 'docker.sock')"

t05_record 6 "relay script in proxy" "$(docker exec "${PROXY}" cat "${RELAY_SCRIPT}" 2>&1 | tr '\n' '|')"
t05_record 6 "proxy listening on :${RELAY_PORT}" "$(docker exec "${PROXY}" netstat -ltn 2>/dev/null | grep -c ":${RELAY_PORT}")"
t05_record 6 "relay inner connect (proxy -> upstream by name)" \
  "$(docker exec "${PROXY}" sh -c "printf 'PING\r\n' | nc -w 3 ${UPSTREAM} ${ENTRY_PORT}" 2>&1 | tr -d '\r\n')"
t05_record 6 "workload -> proxy:${RELAY_PORT} raw connect" \
  "$(docker exec "${WORKLOAD}" bash -c "exec 3<>/dev/tcp/${PROXY}/${RELAY_PORT} && echo CONNECTED || echo REFUSED" 2>&1 | tr -d '\r\n')"
ACCEPTED_BEFORE="$(t05_accepted_from "${PROXY_EGRESS_IP}" "${UPSTREAM}")"
PINGS_BEFORE="$(t05_pings_from "${PROXY_EGRESS_IP}" "${UPSTREAM}")"
t05_record 6 "workload -> proxy:${RELAY_PORT} -> upstream reply (1st)" "$(t05_forward_probe)"
t05_record 6 "workload -> proxy:${RELAY_PORT} -> upstream reply (2nd)" "$(t05_forward_probe)"
t05_record 6 "upstream log: Accepted from proxy (before -> after)" \
  "${ACCEPTED_BEFORE} -> $(t05_accepted_from "${PROXY_EGRESS_IP}" "${UPSTREAM}")"
t05_record 6 "upstream log line for the forwarded request" \
  "$(docker logs "${UPSTREAM}" 2>&1 | grep "Accepted ${PROXY_EGRESS_IP}" | tail -1)"
t05_record 6 "upstream log: cmd=ping from proxy (before -> after)" \
  "${PINGS_BEFORE} -> $(t05_pings_from "${PROXY_EGRESS_IP}" "${UPSTREAM}")"

t05_record 7 "proxy private file visible in workload" \
  "$(docker exec "${WORKLOAD}" bash -c "test -e ${SECRET_IN_PROXY} && echo VISIBLE || echo ABSENT")"
t05_record 7 "workload mounts matching the private file" \
  "$(docker inspect -f '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' "${WORKLOAD}" | grep -c 'fake-provider')"
t05_record 7 "proxy process list" "$(docker exec "${PROXY}" ps -o pid,args 2>&1 | tr '\n' '|')"
t05_record 7 "processes with proxy marker seen from workload / from proxy (control)" \
  "$(t05_marker_count "${WORKLOAD}" bash) / $(t05_marker_count "${PROXY}" sh)"
t05_record 7 "sentinel hits in workload env / argv" \
  "$(docker exec "${WORKLOAD}" bash -c "env | grep -c ${SENTINEL}; tr '\0' ' ' < /proc/1/cmdline | grep -c ${SENTINEL}" | tr '\n' '/' | sed 's:/$::')"

t05_record 8 "image identity workload / listener" \
  "$(docker image inspect -f '{{.Id}}' "${WORKLOAD_IMAGE}") $(docker image inspect -f '{{.Id}}' "${LISTENER_IMAGE}")"
t05_record 8 "container identity" \
  "$(docker inspect -f '{{.Name}} {{.Id}}' "${WORKLOAD}" "${PROXY}" "${UPSTREAM}" "${OTHER}" | tr '\n' ' ')"
t05_record 8 "network identity" \
  "$(docker network inspect -f '{{.Name}} {{.Id}} internal={{.Internal}}' "${INT}" "${EGR}" "${OTH}" | tr '\n' ' ')"

echo "== cleanup =="
t05_cleanup
t05_record 9 "remaining containers with label" "$(docker ps -a --filter "label=${LABEL_TASK}" --format '{{.Names}}' | tr '\n' ' ')"
t05_record 9 "remaining networks with label" "$(docker network ls --filter "label=${LABEL_TASK}" --format '{{.Name}}' | tr '\n' ' ')"
t05_record 9 "remaining volumes with label" "$(docker volume ls --filter "label=${LABEL_TASK}" --format '{{.Name}}' | tr '\n' ' ')"

# --- verdicts ---------------------------------------------------------------------------
echo "== verdicts =="
t05_verify
verdict=$?

echo "transcript: ${TRANSCRIPT}"
if [ -n "${SUFFIX}" ]; then
  echo "-- negative-control mode: the a2/a3 FAIL lines above are the expected outcome --"
  if [ "$(t05_val 'public 1.1.1.1')" = "OPEN" ] || [ "$(t05_val '^3	workload -> fake upstream')" = "OPEN" ]; then
    echo "status=negative-control-ok (the deliberate leak was detected)"
    exit 0
  fi
  echo "status=negative-control-failed (a deliberate leak was NOT detected)"
  exit 1
fi
[ "${verdict}" -eq 0 ] && echo "status=verified" || echo "status=contradicted"
exit "${verdict}"
