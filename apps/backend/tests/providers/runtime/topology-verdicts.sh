#!/usr/bin/env bash
# What a pass means for each assertion the probe records. Kept apart from the probe itself so
# the two lists can be reviewed separately: the probe observes, this file decides.
#
# Add an expectation only by adding a line here, and never loosen one to make a run pass.

T05_VERDICT=0

t05_expect() {
  if [ "$2" = "$3" ]; then
    echo "PASS $1"
  else
    echo "FAIL $1: got '$2' want '$3'"
    T05_VERDICT=1
  fi
}

t05_verify() {
  T05_VERDICT=0
  t05_expect "a1 workload to proxy entry" "$(t05_val '^1	workload -> proxy entry')" "OPEN"
  t05_expect "a1 ping reply" "$(t05_val '^1	  ping reply byte')" "+PONG"
  t05_expect "a2 public 1.1.1.1" "$(t05_val 'public 1.1.1.1')" "CLOSED"
  t05_expect "a2 public 223.5.5.5" "$(t05_val 'public 223.5.5.5')" "CLOSED"
  t05_expect "a3 host gateway" "$(t05_val 'host gateway')" "CLOSED"
  t05_expect "a3 metadata" "$(t05_val 'metadata')" "CLOSED"
  t05_expect "a3 other trial" "$(t05_val 'other trial')" "CLOSED"
  t05_expect "a3 fake upstream from workload" "$(t05_val '^3	workload -> fake upstream')" "CLOSED"
  t05_expect "a4 proxy to upstream" "$(t05_val '^4	proxy -> fake upstream')" "PONG"
  t05_expect "a5 no published ports" "$(t05_val 'published ports' | grep -o '{}' | wc -l | tr -d ' ')" "4"
  t05_expect "a5 no docker socket" "$(t05_val 'docker.sock mount sources')" "0"
  t05_expect "a5 workload has no mounts" "$(t05_val '^5	workload mounts')" "[]"
  t05_expect "a6 relay script targets upstream" "$(t05_val 'relay script in proxy' | grep -c 'nc ')" "1"
  t05_expect "a6 proxy listening on relay port" "$(t05_val 'proxy listening')" "1"
  t05_expect "a6 relay inner connect" "$(t05_val 'relay inner connect')" "+PONG"
  t05_expect "a6 raw connect from workload" "$(t05_val 'raw connect')" "CONNECTED"
  t05_expect "a6 reply through proxy (1st)" "$(t05_val 'upstream reply (1st)')" "+PONG"
  t05_expect "a6 reply through proxy (2nd)" "$(t05_val 'upstream reply (2nd)')" "+PONG"
  t05_expect "a6 accepted delta" "$(t05_val 'Accepted from proxy' | awk '{print $3-$1}')" "2"
  t05_expect "a6 cmd=ping delta" "$(t05_val 'cmd=ping from proxy' | awk '{print $3-$1}')" "2"
  t05_expect "a7 private file" "$(t05_val 'private file visible')" "ABSENT"
  t05_expect "a7 workload mounts match" "$(t05_val 'mounts matching the private file')" "0"
  t05_expect "a7 marker seen from workload" "$(t05_val 'proxy marker seen from workload' | awk '{print $1}')" "0"
  t05_expect "a7 marker scan control (proxy)" "$(t05_val 'proxy marker seen from workload' | awk '{print $3}')" "1"
  t05_expect "a7 sentinel hits" "$(t05_val 'sentinel hits')" "0/0"
  t05_expect "a9 containers remainder" "$(t05_val 'remaining containers')" ""
  t05_expect "a9 networks remainder" "$(t05_val 'remaining networks')" ""
  t05_expect "a9 volumes remainder" "$(t05_val 'remaining volumes')" ""
  return "${T05_VERDICT}"
}
