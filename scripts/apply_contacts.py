#!/usr/bin/env python3
"""
Load the scenario's contact plan into every running ION node with ABSOLUTE
UTC times, so all nodes agree on window boundaries regardless of start order.

Usage: python3 apply_contacts.py <scenario_base_dir> [lead_seconds=15]

Reads  <base>/contacts.def   lines: rel_start rel_end from to rate
Writes <base>/t0.txt         (T0 as unix epoch, for experiment runners)
Writes <base>/contacts_abs.ionrc  then runs `ionadmin contacts_abs.ionrc`
       from inside every n*/ directory (cwd selects the node).

This same mechanism is how the M6 LunaFlow controller will inject policy:
contact-plan updates at runtime through the standard admin interface.
"""
import os, subprocess, sys, time
from datetime import datetime, timezone

def ion_time(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y/%m/%d-%H:%M:%S")

def main():
    base = os.path.abspath(sys.argv[1])
    lead = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    t0 = int(time.time()) + lead
    open(f"{base}/t0.txt", "w").write(str(t0))

    lines = []
    for ln in open(f"{base}/contacts.def"):
        a, b, frm, to, rate = ln.split()
        lines.append(f"a contact {ion_time(t0 + int(a))} {ion_time(t0 + int(b))} {frm} {to} {rate}")
    rc = f"{base}/contacts_abs.ionrc"
    open(rc, "w").write("\n".join(lines) + "\n")

    node_dirs = sorted(d for d in os.listdir(base)
                       if d.startswith("n") and d[1:].isdigit())
    failed = []
    for d in node_dirs:
        r = subprocess.run(["ionadmin", rc], cwd=f"{base}/{d}",
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            failed.append((d, r.stderr.strip()[-200:]))
    if failed:
        for d, err in failed:
            print(f"[apply_contacts] FAIL {d}: {err}")
        sys.exit(1)
    print(f"[apply_contacts] {len(lines)} contact entries -> {len(node_dirs)} nodes, "
          f"T0={t0} ({ion_time(t0)} UTC)")

if __name__ == "__main__":
    main()
