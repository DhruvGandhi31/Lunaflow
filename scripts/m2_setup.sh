#!/usr/bin/env bash
# LunaFlow M2 — store-and-forward chain: probe(10) -> relay(20) -> ground(30)
# Generates all node configs under ~/testbed/m2. Run once; re-run safe (wipes m2 dir).
#
# The physics is in global.ionrc:
#   window A (+10..+40):  probe <-> relay visible   (surface pass)
#   GAP     (+40..+90):   relay sees NOBODY         <- bundle must WAIT here
#   window B (+90..+150): relay <-> ground visible  (Earth in view)
# Times are relative to each node's ionadmin start, so start all nodes quickly.

set -e
BASE=$HOME/testbed/m2
rm -rf $BASE && mkdir -p $BASE

# ---- shared contact plan ----
cat > $BASE/global.ionrc <<'EOF'
a contact +10 +40 10 20 10000
a contact +10 +40 20 10 10000
a contact +90 +150 20 30 20000
a contact +90 +150 30 20 20000
a range +0 +3600 10 20 1
a range +0 +3600 20 10 1
a range +0 +3600 20 30 1
a range +0 +3600 30 20 1
EOF

# ---- per-node configs ----
# node : port : wmKey : sdrWmKey
for spec in "10:4610:66210:65290" "20:4620:66220:65291" "30:4630:66230:65292"; do
  IFS=: read N PORT WMKEY SDRWMKEY <<< "$spec"
  D=$BASE/n$N && mkdir -p $D

  cat > $D/node.ionconfig <<EOF
wmKey $WMKEY
sdrName ion$N
sdrWmKey $SDRWMKEY
wmSize 5000000
configFlags 1
heapWords 250000
pathName /tmp
EOF

  cat > $D/node.ionrc <<EOF
1 $N node.ionconfig
s
m horizon +0
EOF

  echo "1" > $D/node.ionsecrc
  cp $BASE/global.ionrc $D/global.ionrc

  # neighbors: probe<->relay, relay<->ground
  case $N in
    10) DUCTS="a outduct udp 127.0.0.1:4620 udpclo"
        PLANS="a plan 20 udp/127.0.0.1:4620" ;;
    20) DUCTS="a outduct udp 127.0.0.1:4610 udpclo
a outduct udp 127.0.0.1:4630 udpclo"
        PLANS="a plan 10 udp/127.0.0.1:4610
a plan 30 udp/127.0.0.1:4630" ;;
    30) DUCTS="a outduct udp 127.0.0.1:4620 udpclo"
        PLANS="a plan 20 udp/127.0.0.1:4620" ;;
  esac

  cat > $D/node.bprc <<EOF
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:$N.0 q
a endpoint ipn:$N.1 q
a endpoint ipn:$N.2 q
a protocol udp 1400 100
a induct udp 0.0.0.0:$PORT udpcli
$DUCTS
r 'ipnadmin node.ipnrc'
w 1
s
EOF

  echo "$PLANS" > $D/node.ipnrc
done

echo "M2 scenario generated in $BASE"
echo "Next: export ION_NODE_LIST_DIR=$BASE   then run m2_run.sh"
