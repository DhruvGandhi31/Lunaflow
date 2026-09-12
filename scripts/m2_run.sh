#!/usr/bin/env bash
# LunaFlow M2 — timed experiment: watch a bundle wait out a coverage gap.
# Prereq: m2_setup.sh already run. WARNING: killm f tears down ALL ION nodes on host.

BASE=$HOME/testbed/m2
export ION_NODE_LIST_DIR=$BASE
ts() { echo "[T+$(( $(date +%s) - T0 ))s] $*"; }

echo "=== reset ==="
killm f >/dev/null 2>&1
rm -f /dev/shm/sem.ion* $BASE/ion_nodes

echo "=== starting nodes 10, 20, 30 ==="
T0=$(date +%s)
for N in 10 20 30; do
  (cd $BASE/n$N && ionadmin node.ionrc && ionadmin global.ionrc \
    && ionsecadmin node.ionsecrc && bpadmin node.bprc) > $BASE/n$N/start.log 2>&1
  ts "node $N up"
done
cat $BASE/ion_nodes
ss -ulpn | grep -E "4610|4620|4630"   # expect exactly 3 udpcli lines

echo "=== ground station listening (node 30) ==="
(cd $BASE/n30 && stdbuf -oL bpsink ipn:30.1 > $BASE/ground_rx.log 2>&1 &)

# --- t=15: inside window A. Probe transmits its science packet. ---
sleep $(( 15 - ($(date +%s) - T0) ))
ts "PROBE SENDS: window probe->relay is open (relay->ground is NOT)"
(cd $BASE/n10 && bpsource ipn:30.1 "FARSIDE-SCIENCE-001 sent at T+$(( $(date +%s) - T0 ))s" -t3600)

# --- t=25: bundle should have hopped to the relay already ---
sleep $(( 25 - ($(date +%s) - T0) ))
ts "relay bundle count (expect >=1, dest ipn:30.1):"
(cd $BASE/n20 && bplist 2>/dev/null | grep -E "Destination|\*\*\*\* Bundle" | head -6)

# --- t=55: THE GAP. Window A closed, window B not yet open. ---
sleep $(( 55 - ($(date +%s) - T0) ))
ts "IN THE GAP: no contact exists anywhere. Bundle must be parked at relay."
(cd $BASE/n20 && bplist 2>/dev/null | grep -c "\*\*\*\* Bundle") | xargs -I{} echo "   bundles stored at relay: {}"
echo "   payloads at ground so far: $(grep -c FARSIDE $BASE/ground_rx.log)  <- must be 0"

# --- t=100: window B open. Relay should have transmitted. ---
sleep $(( 100 - ($(date +%s) - T0) ))
ts "WINDOW B OPEN: relay->ground contact active since T+90"
sleep 5
echo "=== ground_rx.log ==="
cat $BASE/ground_rx.log
echo "======================"
if grep -q "FARSIDE-SCIENCE-001" $BASE/ground_rx.log; then
  ts "M2 PASS: bundle sent at T+15 crossed a 50s coverage gap and was delivered after T+90."
else
  ts "M2 FAIL: not delivered. Check $BASE/n20/ion.log and $BASE/n30/ion.log"
fi
killm f >/dev/null 2>&1
