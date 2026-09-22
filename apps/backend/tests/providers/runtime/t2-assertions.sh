#!/usr/bin/env bash
# Task 05 T2: the half of the seven assertions that must run *inside* Harbor's workload
# container, given as that Trial's command.
#
# Why this is not topology-probe.sh: that one creates the containers itself (pure Docker
# layer, T1). Here Harbor creates them and this script only observes -- the container it
# runs in is the workload, the proxy and fake upstream are sibling services, and the
# readings that need the Docker API (published ports, mounts, the private file, cleanup)
# are taken on the host after the run, as the runbook's appendix three requires.
#
# It prints raw readings, then its own PASS/FAIL verdicts alongside the same expectation
# names topology-verdicts.sh uses, so the two lists can be reviewed together. It never
# loosens an expectation to make a run pass.
#
# NOT RUN ON THE DEVELOPMENT MACHINE: this machine has no framework/harbor and no running
# Docker daemon, so this script has only been syntax-checked (bash -n) here. Its first real
# run is the owner's next T2 round, and that run's actual output is the evidence.
#
# Environment (set them in the Trial command; defaults match the shape in runbook appendix
# three, where the services are named proxy and fake-upstream):
#   T05_PROXY_HOST        default proxy            T05_PROXY_PORT        default 8080
#   T05_UPSTREAM_HOST     default fake-upstream    T05_UPSTREAM_PORT     default 8080
#   T05_OTHER_TRIAL_HOST  default t05-other-trial  T05_OTHER_TRIAL_PORT  default 6379
#   T05_PRIVATE_MARKER    default FAKE-T05-PROVIDER-SECRET
#   T05_SENTINEL          default FAKE-T05-CLIENT-TOKEN
#   T05_PRIVATE_PATH      default /opt/agentexam-private/fake-provider.json (the provider
#                         file stays on the host; the workload asserts it is not visible here)
set -uo pipefail

PROXY_HOST="${T05_PROXY_HOST:-proxy}"
PROXY_PORT="${T05_PROXY_PORT:-8080}"
UPSTREAM_HOST="${T05_UPSTREAM_HOST:-fake-upstream}"
UPSTREAM_PORT="${T05_UPSTREAM_PORT:-8080}"
OTHER_HOST="${T05_OTHER_TRIAL_HOST:-t05-other-trial}"
OTHER_PORT="${T05_OTHER_TRIAL_PORT:-6379}"
MARKER="${T05_PRIVATE_MARKER:-FAKE-T05-PROVIDER-SECRET}"
SENTINEL="${T05_SENTINEL:-FAKE-T05-CLIENT-TOKEN}"
PRIVATE_PATH="${T05_PRIVATE_PATH:-/opt/agentexam-private/fake-provider.json}"

T05_VERDICT=0

# How many processes expose the marker, in one /proc field. The pattern is bracketed so this
# scan cannot match its own command line, and the scan is bounded to /proc: a recursive grep
# over /home or /etc is unbounded and would eat the Trial's wall clock instead of reporting.
t05_marker_count() {
  local field="$1" pattern count=0 file
  pattern="$(printf '%s' "${MARKER}" | sed 's/./[&]/1')"
  for file in /proc/[0-9]*/"${field}"; do
    [ -r "${file}" ] || continue
    tr '\0' ' ' < "${file}" 2>/dev/null | grep -q "${pattern}" && count=$((count + 1))
  done
  echo "${count}"
}

# Raw TCP open test. bash's /dev/tcp is the only tool the workload is guaranteed to have,
# and `timeout` is required around it: without one, a filtered address holds the connection
# until the kernel gives up, which would eat the Trial's wall clock instead of reporting.
t05_tcp() {
  local host="$1" port="$2"
  timeout 3 bash -c "exec 3<>/dev/tcp/${host}/${port}" >/dev/null 2>&1 &&
    echo OPEN || echo CLOSED
}

# One relayed request: the reply has to come back from the fake upstream, so this also
# proves the proxy is not answering from its own pocket.
t05_through_proxy() {
  local reply
  reply="$(timeout 5 bash -c "
    exec 3<>/dev/tcp/${PROXY_HOST}/${PROXY_PORT} || exit 1
    printf 'PING\n' >&3
    head -c 16 <&3
  " 2>/dev/null | tr -d '\r\n')"
  case "${reply}" in
    *+PONG*) echo "PONG" ;;
    "") echo "NO-REPLY" ;;
    *) echo "${reply}" ;;
  esac
}

t05_expect() {
  if [ "$2" = "$3" ]; then
    echo "PASS $1"
  else
    echo "FAIL $1: got '$2' want '$3'"
    T05_VERDICT=1
  fi
}

echo "readings"
echo "1	workload -> proxy entry	$(t05_tcp "${PROXY_HOST}" "${PROXY_PORT}")"
echo "1	  reply through proxy	$(t05_through_proxy)"
echo "2	public 1.1.1.1	$(t05_tcp 1.1.1.1 443)"
echo "2	public 223.5.5.5	$(t05_tcp 223.5.5.5 443)"
echo "3	workload -> fake upstream	$(t05_tcp "${UPSTREAM_HOST}" "${UPSTREAM_PORT}")"
echo "3	workload -> other trial	$(t05_tcp "${OTHER_HOST}" "${OTHER_PORT}")"
echo "3	host gateway	$(t05_tcp host.docker.internal 80)"
echo "3	metadata	$(t05_tcp 169.254.169.254 80)"
echo "7	private path	$([ -e "${PRIVATE_PATH}" ] && echo PRESENT || echo ABSENT)"
echo "7	marker in /proc/*/environ	$(t05_marker_count environ)"
echo "7	marker in /proc/*/cmdline	$(t05_marker_count cmdline)"
echo "7	sentinel files	$(timeout 10 grep -rla "${SENTINEL}" /tmp /run /var/tmp 2>/dev/null | wc -l | tr -d ' ')"
echo "7	docker.sock present	$([ -S /var/run/docker.sock ] && echo yes || echo no)"
echo "verdicts"

# a1: the workload reaches the proxy, and only through it does it see an answer.
t05_expect "a1 workload to proxy entry" "$(t05_tcp "${PROXY_HOST}" "${PROXY_PORT}")" "OPEN"
t05_expect "a1 reply through proxy" "$(t05_through_proxy)" "PONG"
# a2: no public egress of its own.
t05_expect "a2 public 1.1.1.1" "$(t05_tcp 1.1.1.1 443)" "CLOSED"
t05_expect "a2 public 223.5.5.5" "$(t05_tcp 223.5.5.5 443)" "CLOSED"
# a3: no side doors, and not even the fake upstream directly.
t05_expect "a3 workload -> fake upstream" "$(t05_tcp "${UPSTREAM_HOST}" "${UPSTREAM_PORT}")" "CLOSED"
t05_expect "a3 workload -> other trial" "$(t05_tcp "${OTHER_HOST}" "${OTHER_PORT}")" "CLOSED"
t05_expect "a3 host gateway" "$(t05_tcp host.docker.internal 80)" "CLOSED"
t05_expect "a3 metadata" "$(t05_tcp 169.254.169.254 80)" "CLOSED"
# a7: the provider secret is not reachable from the workload.
t05_expect "a7 private path" "$([ -e "${PRIVATE_PATH}" ] && echo PRESENT || echo ABSENT)" "ABSENT"
t05_expect "a7 marker in environment" "$(t05_marker_count environ)" "0"
t05_expect "a7 marker in argv" "$(t05_marker_count cmdline)" "0"
t05_expect "a7 sentinel files" "$(timeout 10 grep -rla "${SENTINEL}" /tmp /run /var/tmp 2>/dev/null | wc -l | tr -d ' ')" "0"
t05_expect "a7 no docker socket" "$([ -S /var/run/docker.sock ] && echo yes || echo no)" "no"

echo "status=$([ "${T05_VERDICT}" -eq 0 ] && echo verified || echo failed)"
exit "${T05_VERDICT}"
