#!/usr/bin/env python3
"""
LunaFlow M3 -- scenario generator.

JSON scenario description -> full ION config tree + start/stop scripts.

Usage:  python3 genscenario.py <scenario.json> [output_base_dir]

Key design choice: contact WINDOWS are not baked into per-node startup configs.
With N nodes started sequentially, ionadmin's relative times ("+10") would skew
by a few seconds per node -- at 17 nodes the network would disagree about when
windows open. Instead:
  1. start_all.sh boots every node with only its identity + ranges,
  2. apply_contacts.py then loads the SAME absolute-UTC contact plan into
     every node, computed from a shared T0 = now + lead.
Runtime contact-plan injection is also exactly how the M6 LunaFlow controller
will operate, so this pipeline is reused there.

Scenario JSON format (see scenarios/*.json):
{
  "name": "m3_smoke",
  "duration": 600,                     # scenario length, seconds
  "owlt": 1,                           # default one-way light time, seconds
  "nodes": [
    {"id": 101, "type": "probe"},
    {"id": 20,  "type": "relay", "buffer_mb": 4},   # buffer_mb = bundle storage cap
    {"id": 30,  "type": "ground"}
  ],
  "contacts": [
    # periodic form: windows [offset+k*period, +duration] until 'until'|duration
    {"from": 101, "to": 20, "period": 120, "offset": 10, "duration": 30, "rate": 10000},
    # explicit form:
    {"from": 20, "to": 30, "windows": [[60, 100], [180, 220]], "rate": 20000}
    # both default bidir: true; "owlt" per-contact override allowed
  ],
  "traffic": {...}                     # ignored here; read by run_experiment.py (M4)
}

Bundle storage caps (buffer_mb) -- verified against ION source, see docs/M4.md:
  * heapWords alone does NOT cap storage: by default ION acquires any received
    bundle > 560 bytes into FILE space, whose limit defaults to 1 TB.
  * A node's bundles live in two ZCO pools: inbound (just received) and
    outbound (queued for forwarding / locally sourced).
  * buffer_mb = B therefore emits, for that node:
        ionadmin  m inbound  ceil(B/2) 0    (heap MB, file MB = 0)
        ionadmin  m outbound floor(B/2) 0
        bpadmin   m heapmax  65000          (acquire every UDP bundle into heap)
    and grows heapWords so each pool limit is accepted (ION caps any one pool
    at 40% of the heap: 60% is sequestered as margin + operating allocation).
"""
import json, math, os, shutil, stat, sys

PORT_BASE = 4000                      # node id N listens on 4000+N
def port(n):     return PORT_BASE + n
def wm_key(n):   return 70000 + n     # away from ION defaults (65280/65281)
def sdrwm_key(n):return 72000 + n

DEFAULT_HEAP_WORDS = 250000
WORD_BYTES = 8                        # x86_64
ION_USABLE_HEAP = 0.40                # 100% - ION_SEQUESTERED (20 margin + 40 ops)
HEAPMAX = 65000                       # > largest UDP bundle (UDPCLA_BUFSZ = 65535)

def storage_plan(n):
    """-> (heap_words, inbound_mb, outbound_mb) ; mb values None if uncapped."""
    heap = n.get("heap_words", DEFAULT_HEAP_WORDS)
    b = n.get("buffer_mb")
    if b is None:
        return heap, None, None
    assert isinstance(b, int) and b >= 2, f"node {n['id']}: buffer_mb must be an int >= 2"
    inb, outb = math.ceil(b / 2), b // 2
    # whole cap must fit in the usable heap, with 25% headroom for bundle objects
    need = math.ceil(b * 1e6 * 1.25 / ION_USABLE_HEAP / WORD_BYTES)
    return max(heap, need), inb, outb

def expand_contacts(scn):
    """-> list of (start, end, from, to, rate, owlt), directional."""
    out = []
    for c in scn["contacts"]:
        rate = c.get("rate", 10000)
        owlt = c.get("owlt", scn.get("owlt", 1))
        pairs = [(c["from"], c["to"])]
        if c.get("bidir", True):
            pairs.append((c["to"], c["from"]))
        if "windows" in c:
            wins = c["windows"]
        else:
            wins, t = [], c.get("offset", 0)
            until = c.get("until", scn["duration"])
            while t < until:
                wins.append([t, min(t + c["duration"], until)])
                t += c["period"]
        for a, b in wins:
            for f, to in pairs:
                out.append((a, b, f, to, rate, owlt))
    return sorted(out)

def neighbors(node_id, contacts):
    return sorted({to for (_, _, f, to, _, _) in contacts if f == node_id})

def main():
    scn = json.load(open(sys.argv[1]))
    base = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2
                              else f"~/testbed/{scn['name']}")
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)

    contacts = expand_contacts(scn)
    ids = [n["id"] for n in scn["nodes"]]
    assert len(ids) == len(set(ids)), "duplicate node ids"

    # ---- contacts.def: relative windows, consumed by apply_contacts.py ----
    with open(f"{base}/contacts.def", "w") as f:
        for (a, b, frm, to, rate, _) in contacts:
            f.write(f"{a} {b} {frm} {to} {rate}\n")

    # ---- per-node config dirs ----
    for n in scn["nodes"]:
        nid = n["id"]
        d = f"{base}/n{nid}"
        os.makedirs(d)
        heap, inb_mb, outb_mb = storage_plan(n)
        capped = inb_mb is not None

        open(f"{d}/node.ionconfig", "w").write(
f"""wmKey {wm_key(nid)}
sdrName ion{nid}
sdrWmKey {sdrwm_key(nid)}
wmSize 5000000
configFlags 1
heapWords {heap}
pathName /tmp
""")
        open(f"{d}/node.ionrc", "w").write(
f"""1 {nid} node.ionconfig
s
m horizon +0
""" + (f"m inbound {inb_mb} 0\nm outbound {outb_mb} 0\n" if capped else ""))
        # ranges (OWLT) are time-invariant -> loaded at startup, relative times fine
        with open(f"{d}/ranges.ionrc", "w") as f:
            seen = set()
            for (_, _, frm, to, _, owlt) in contacts:
                if (frm, to) not in seen:
                    seen.add((frm, to))
                    f.write(f"a range +0 +{scn['duration'] + 100000} {frm} {to} {owlt}\n")
        open(f"{d}/node.ionsecrc", "w").write("1\n")

        nbrs = neighbors(nid, contacts)
        ducts = "\n".join(f"a outduct udp 127.0.0.1:{port(x)} udpclo" for x in nbrs)
        open(f"{d}/node.bprc", "w").write(
f"""1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:{nid}.0 q
a endpoint ipn:{nid}.1 q
a endpoint ipn:{nid}.2 q
a endpoint ipn:{nid}.3 q
a protocol udp 1400 100
a induct udp 0.0.0.0:{port(nid)} udpcli
{ducts}
r 'ipnadmin node.ipnrc'
{f"m heapmax {HEAPMAX}" + chr(10) if capped else ""}w 1
s
""")
        open(f"{d}/node.ipnrc", "w").write(
            "\n".join(f"a plan {x} udp/127.0.0.1:{port(x)}" for x in nbrs) + "\n")

    # ---- start/stop scripts ----
    # relays+ground first (they're everyone's next hop), probes after
    order = sorted(scn["nodes"], key=lambda n: 0 if n.get("type") in ("relay", "ground") else 1)
    starts = "\n".join(
        f'(cd $BASE/n{n["id"]} && ionadmin node.ionrc && ionadmin ranges.ionrc '
        f'&& ionsecadmin node.ionsecrc && bpadmin node.bprc) > $BASE/n{n["id"]}/start.log 2>&1 '
        f'&& echo "  node {n["id"]} ({n.get("type","?")}) up"'
        for n in order)
    open(f"{base}/start_all.sh", "w").write(
f"""#!/usr/bin/env bash
# Generated by genscenario.py for scenario '{scn["name"]}'. Boots all {len(ids)} nodes,
# then applies the absolute-time contact plan. WARNING: killm f kills ALL ION on host.
BASE=$(cd $(dirname $0) && pwd)
export ION_NODE_LIST_DIR=$BASE
echo "=== reset ==="
killm f >/dev/null 2>&1; rm -f /dev/shm/sem.ion* $BASE/ion_nodes
echo "=== starting {len(ids)} nodes ==="
{starts}
UP=$(wc -l < $BASE/ion_nodes 2>/dev/null || echo 0)
echo "=== registry ($UP/{len(ids)}) ==="
cat $BASE/ion_nodes
if [ "$UP" -ne {len(ids)} ]; then
  echo "start_all: only $UP/{len(ids)} nodes registered -- see n<id>/start.log" >&2
  exit 1
fi
echo "=== applying contact plan (T0 = now + ${{1:-15}}s) ==="
python3 $BASE/apply_contacts.py $BASE ${{1:-15}} || exit 1
echo "T0 epoch: $(cat $BASE/t0.txt)"
""")
    os.chmod(f"{base}/start_all.sh", 0o755)
    open(f"{base}/stop_all.sh", "w").write("#!/usr/bin/env bash\nkillm f\nrm -f /dev/shm/sem.ion* $(dirname $0)/ion_nodes\n")
    os.chmod(f"{base}/stop_all.sh", 0o755)

    # apply_contacts.py rides along inside the scenario dir
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "apply_contacts.py"), base)
    shutil.copy(sys.argv[1], f"{base}/scenario.json")

    for n in scn["nodes"]:
        heap, inb_mb, outb_mb = storage_plan(n)
        if inb_mb is not None:
            print(f"[genscenario] node {n['id']}: storage cap {inb_mb}+{outb_mb} MB "
                  f"(inbound+outbound), heapWords {heap}")

    n_win = len({(a, b) for (a, b, *_ ) in contacts})
    print(f"[genscenario] {scn['name']}: {len(ids)} nodes, {n_win} contact windows "
          f"({len(contacts)} directional entries), duration {scn['duration']}s")
    print(f"[genscenario] output: {base}")
    print(f"[genscenario] run:    {base}/start_all.sh")

if __name__ == "__main__":
    main()
