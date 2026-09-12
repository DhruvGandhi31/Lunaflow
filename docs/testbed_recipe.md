# LunaFlow Testbed — Working Recipe (Milestone 1 complete)

Verified 24 Aug 2026 in Linux sandbox (Ubuntu 22.04, gcc 11, no root, no docker).
Result: 2 ION nodes on one host, UDP convergence layer, bping 3/3 bundles, ~3.6 ms avg RTT.

## Build ION (no root needed)

```bash
git clone --depth 1 https://github.com/nasa-jpl/ION-DTN.git
cd ION-DTN
./enable_manual_build.sh --skip-clean   # switches to manual Makefiles (no autotools needed)
make all                                 # ~5 min; builds bpv7, ltp, cgr, all daemons
# make install needs /usr/local; instead collect binaries manually:
mkdir -p $HOME/ion/bin $HOME/ion/lib
find . -path "*/x86_64-linux/bin/*" -type f -exec cp {} $HOME/ion/bin/ \;
find . -path "*/x86_64-linux/lib/*" -name "*.so*" -exec cp {} $HOME/ion/lib/ \;
export PATH=$HOME/ion/bin:$PATH LD_LIBRARY_PATH=$HOME/ion/lib
```

## Multi-node-on-one-host pattern (the key trick)

Known-good reference: `ION-DTN/tests/multinode-sdrwmkey/` (copy its `2.ipn.ltp/`, `3.ipn.ltp/` dirs).

1. `export ION_NODE_LIST_DIR=$PWD` (parent dir of all node dirs); delete stale `./ion_nodes`.
2. One directory per node. Apps select their node by **current working directory** (registered in `ion_nodes`).
3. Each node needs a unique `*.ionconfig`:

```
wmKey 66236        # unique per node
sdrName ion2       # unique per node
sdrWmKey 65282     # unique per node
wmSize 5000000
configFlags 1
heapWords 250000
pathName /tmp
```

4. Per node: `amroc.ionrc` (first line `1 <nodenum> amroc.ionconfig`), `global.ionrc` (shared contact plan), `amroc.ionsecrc`, `amroc.bprc` (endpoints + UDP induct on unique port + outducts to peers' ports), `amroc.ipnrc` (`a plan <node> udp/127.0.0.1:<port>`).
5. Start each: `cd nodedir && ionadmin amroc.ionrc && ionadmin global.ionrc && ionsecadmin amroc.ionsecrc && bpadmin amroc.bprc`.
6. Verify: `(cd node3dir && bpecho ipn:3.1 &)` then `(cd node2dir && bping -c 3 -i 1 ipn:2.2 ipn:3.1)`.
7. Teardown: `killm` (kills ALL nodes on host).

Contact plan syntax (global.ionrc): `a contact +START +END FROM TO RATE_bytes/sec`, `a range +START +END FROM TO OWLT_sec`. Time-limited contacts (`+10 +60`) are how we script intermittency — this is the lever for the dawn-flush scenario.

## Gotchas learned

- `extract.sh` in ion-core fails behind proxy (tarball download blocked); clone full ION-DTN via git instead.
- Single-node bpsource→bpsink loopback does NOT deliver in this build — don't debug it; the multi-node UDP path is the supported pattern (node 2 self-loopback via its own UDP induct works fine).
- Each node's `pathName` in ionconfig can stay `/tmp`; `ion.log` is written to the node's cwd.
- Sandbox is ephemeral: re-run build steps in a fresh session, or run on your own Linux/WSL2 machine (note: README mentions a WSL2 networking quirk — check it if testing on Windows).

## Roadmap

- [x] **M1: 2 nodes, one bundle end-to-end (bping over UDP)** ← done
- [ ] M2: 4-node relay topology (surface → relay → relay/ground) with *time-windowed* contacts; verify store-and-forward across a contact gap (bundle waits at relay until next window opens)
- [ ] M3: Topology generator script (Python): emits per-node config dirs + global.ionrc from a scenario description (~17–20 nodes, ELFO + far-side relay orbits, simplified visibility windows)
- [ ] M4: Traffic + measurement harness: bpdriver/bpcounter or bpsource loops; parse ion.log + bplist for delivery ratio and drop counts; CSV out
- [ ] M5: Dawn-flush scenario on vanilla SABR → baseline plots (delivery ratio, relay buffer occupancy)
- [ ] M6: Enhancement: energy model harness (battery state per node; harness closes contacts when battery empty) + energy/congestion-weighted routing (modify ipnfw/CGR cost or override contact plans dynamically via ionadmin)
- [ ] M7: A/B comparison runs, N seeds → Phase 2 plots
