#!/usr/bin/env bash
# Shared helpers for the task 05 topology probe (see topology-probe.sh). Not product code.
#
# Every check here is written so that a broken harness cannot be mistaken for a topology
# finding: the probes return raw observations, and t05_health_gate refuses to let the driver
# report assertions at all when the containers or listeners are not healthy.

# --- recording -------------------------------------------------------------------------
t05_record() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" | tee -a "${TRANSCRIPT}"; }
t05_val() { grep -e "$1" "${TRANSCRIPT}" | head -1 | cut -f3; }

# --- reachability probes ---------------------------------------------------------------
# Raw TCP open test, from a container that has bash and /dev/tcp.
t05_touch_probe() {
  docker exec "$1" timeout 3 bash -c "</dev/tcp/$2/$3" >/dev/null 2>&1 && echo OPEN || echo CLOSED
}
# Raw RESP PING from a bash-bearing container; prints the reply bytes.
t05_ping_probe() {
  docker exec "$1" timeout 3 bash -c "
    exec 3<>/dev/tcp/$2/$3 || exit 1
    printf 'PING\r\n' >&3
    head -c 7 <&3
  " 2>/dev/null | tr -d '\r\n'
}
# The listener image is Alpine: it has neither bash nor /dev/tcp, so a "bash -c" check there
# fails silently and would read as CLOSED. Ask its own redis-cli instead.
t05_redis_ping() { docker exec "$1" redis-cli -h "$2" -p "$3" ping 2>/dev/null | tr -d '\r\n'; }
# One request that must be relayed: the reply comes back from the fake upstream.
t05_forward_probe() {
  docker exec "${WORKLOAD}" bash -c \
    "exec 3<>/dev/tcp/${PROXY}/${RELAY_PORT} && printf 'PING\r\n' >&3 && timeout 5 head -c 7 <&3" 2>&1 \
    | tr -d '\r\n'
}
# Processes whose cmdline matches the proxy marker, seen from inside a given container.
# The caller passes the shell to use: the workload has bash, the listener image only sh.
# MARKER_RE is bracketed so the scanning shell cannot match the pattern it is searching for.
t05_marker_count() {
  docker exec "$1" "$2" -c "c=0; for f in /proc/[0-9]*/cmdline; do \
tr '\0' ' ' < \"\$f\" 2>/dev/null | grep -q ${MARKER_RE} && c=\$((c+1)); done; echo \$c"
}

# --- readings taken outside the containers ---------------------------------------------
t05_net_ip() { docker inspect -f "{{(index .NetworkSettings.Networks \"$2\").IPAddress}}" "$1" 2>/dev/null; }
# Counted from the fake upstream's own log, so measuring costs no connection of its own.
t05_accepted_from() { docker logs "$2" 2>&1 | grep -c "Accepted $1"; }
t05_pings_from() { docker logs "$2" 2>&1 | grep "addr=$1" | grep -c 'cmd=ping'; }

# --- health gate ------------------------------------------------------------------------
# On any problem: write the diagnostics, print them, and return non-zero. The driver then
# exits as harness-failed without emitting a single assertion.
t05_health_gate() {
  local problems=() container status name
  for container in "${WORKLOAD}" "${PROXY}" "${UPSTREAM}" "${OTHER}"; do
    status="$(docker inspect -f '{{.State.Status}}' "${container}" 2>/dev/null)"
    [ "${status}" = "running" ] || problems+=("${container} status=${status:-missing}")
  done
  for name in PROXY_IP OTHER_IP UPSTREAM_IP PROXY_EGRESS_IP; do
    [ -n "${!name}" ] || problems+=("empty address for ${name}")
  done
  [ "$(t05_redis_ping "${PROXY}" 127.0.0.1 "${ENTRY_PORT}")" = "PONG" ] || problems+=("proxy entry not answering")
  [ "$(t05_redis_ping "${UPSTREAM}" 127.0.0.1 "${ENTRY_PORT}")" = "PONG" ] || problems+=("upstream not answering")
  [ "$(t05_redis_ping "${OTHER}" 127.0.0.1 "${ENTRY_PORT}")" = "PONG" ] || problems+=("other trial not answering")
  [ "$(docker exec "${WORKLOAD}" bash -c 'id -u' 2>/dev/null)" = "0" ] || problems+=("workload shell unusable")
  [ "${#problems[@]}" -eq 0 ] && return 0

  {
    echo "harness-failed: ${#problems[@]} problem(s); no assertion was measured"
    printf 'problem: %s\n' "${problems[@]}"
    for container in "${WORKLOAD}" "${PROXY}" "${UPSTREAM}" "${OTHER}"; do
      echo "--- ${container} ---"
      docker inspect -f 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "${container}" 2>&1
      docker logs "${container}" 2>&1 | tail -15
    done
  } > "${DIAG}" 2>&1
  cat "${DIAG}"
  echo "status=harness-failed  (see ${DIAG})"
  return 1
}

# --- cleanup ----------------------------------------------------------------------------
# Only the named resources are removed; there is never a global prune.
t05_cleanup() {
  local container network
  for container in "${WORKLOAD}" "${PROXY}" "${UPSTREAM}" "${OTHER}"; do
    docker rm -f "${container}" >/dev/null 2>&1
  done
  for network in "${INT}" "${EGR}" "${OTH}"; do
    docker network rm "${network}" >/dev/null 2>&1
  done
}
