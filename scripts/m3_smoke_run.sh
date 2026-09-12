#!/usr/bin/env bash
# LunaFlow M3 smoke test: 6 nodes, 3 probes send during window A (T0+10..40),
# relay parks bundles, ground receives during window B (T0+60..100).
# Prereq: python3 genscenario.py m3_smoke.json  was already run.

BASE=$HOME/testbed/m3_smoke
export ION_NODE_LIST_DIR=$BASE
wait_until() { local tgt=$1; local now=$(date +%s); [ $tgt -gt $now ] && sleep $(( tgt - now )); }
ts() { echo "[T0+$(( $(date +%s) - T0 ))s] $*"; }

$BASE/start_all.sh 20 || exit 1          # boot nodes, apply contacts with T0 = now+20s
T0=$(cat $BASE/t0.txt)

(cd $BASE/n30 && stdbuf -oL bpsink ipn:30.1 > $BASE/ground_rx.log 2>&1 &)

wait_until $(( T0 + 15 ))                 # inside window A
ts "probes 101-103 send (window A open, relay->ground closed)"
for P in 101 102 103; do
  (cd $BASE/n$P && bpsource ipn:30.1 "PKT-$P sent at T0+$(( $(date +%s) - T0 ))s" -t3600)
done

wait_until $(( T0 + 50 ))                 # gap: A closed, B not open
ts "gap check -- bundles parked at relay: $(cd $BASE/n20 && bplist 2>/dev/null | grep -c '\*\*\*\* Bundle')  (expect 3)"
ts "gap check -- payloads at ground: $(grep -c PKT- $BASE/ground_rx.log)  (expect 0)"

wait_until $(( T0 + 110 ))                # window B (60..100) has come and gone
echo "=== ground_rx.log ==="; grep "PKT-" $BASE/ground_rx.log
N=$(grep -c "PKT-" $BASE/ground_rx.log)
if [ "$N" -eq 3 ]; then ts "M3 SMOKE PASS: 3/3 bundles crossed the gap via the relay."
else ts "M3 SMOKE FAIL: $N/3 delivered. Check $BASE/n20/ion.log, $BASE/n30/ion.log"; fi
$BASE/stop_all.sh >/dev/null 2>&1
