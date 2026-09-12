# LunaFlow Phase 2 Build Guide — From Testbed to 3-Minute Demo

Timeline: Phase 2 runs **7–27 Sep 2026**. This guide turns the M2–M7 roadmap into a day-by-day plan ending in a submitted video. Each milestone produces a video-usable artifact, so even a partial build yields a complete submission.

**Design principle for the 3 weeks:** no C code changes. SABR routes on whatever contact plan it's given — so LunaFlow v0 is implemented as a **network-management layer** (Python controller) that shapes contact plans and admission through ION's standard admin interfaces. This is honest engineering (it matches your deployment model: ground-segment admin + policy), it's achievable in 3 weeks, and deep CGR modification stays in scope for the thesis.

---

## Schedule at a glance

| Days (Sep) | Milestone | Video artifact produced |
|---|---|---|
| 7–9 | M2: 4-node store-and-forward chain | Terminal clip: bundle waiting at relay during coverage gap |
| 10–12 | M3: Topology generator (~17 nodes) | Network diagram + node startup montage |
| 13–15 | M4: Traffic + measurement harness | CSV pipeline working |
| 16–18 | M5: Dawn-flush baseline on vanilla SABR | **The money plot: SABR under stress** |
| 19–22 | M6: LunaFlow controller (energy + congestion policy) | A/B comparison plots |
| 23–24 | M7: Multi-seed runs, final plots | All figures final |
| 25–27 | Video production + submission | The 3-minute video |

**Fallback rule:** if M6 slips past Sep 22, ship the baseline-only story ("here is the dawn flush breaking NASA's own routing — and here is the LunaFlow design that fixes it"). A real failure demo + credible design beats an unfinished fix.

---

## M2 — Store-and-forward chain (Days 1–3)

**Goal:** prove the atom of the whole experiment: a bundle arrives at a relay *during a coverage gap*, waits in storage, and forwards when the next window opens.

**Topology:** node 10 (far-side probe) → node 20 (relay R2) → node 30 (Earth ground).

**Directory layout** (as in testbed_recipe.md — one dir per node, `ION_NODE_LIST_DIR` set in parent):

```
m2/
  ion_nodes            (auto-created; delete before each run)
  n10/  n20/  n30/     (each: node.ionrc, node.ionconfig, node.ionsecrc, node.bprc, node.ipnrc, global.ionrc)
```

**Per-node ionconfig** (unique keys; pattern: wmKey 6620+N, sdrName ionN, sdrWmKey 0xff00+N):

```
# n10/node.ionconfig
wmKey 66210
sdrName ion10
sdrWmKey 65290
wmSize 5000000
configFlags 1
heapWords 250000
pathName /tmp
```

**The contact plan is where the physics lives** (`global.ionrc`, identical for all nodes). Times are relative (+seconds from ionadmin start). One-way light time Moon→Earth ≈ 1.3 s:

```
# probe 10 sees relay 20 early, briefly (surface pass)
a contact +10 +40 10 20 10000
a range   +0 +3600 10 20 0
# relay 20 sees ground 30 ONLY LATER — this is the gap
a contact +90 +150 20 30 20000
a range   +0 +3600 20 30 1
# (add reverse contacts 20->10, 30->20 with same windows for acks/admin)
a contact +10 +40 20 10 10000
a contact +90 +150 30 20 20000
```

**bprc per node:** UDP induct on its own port (10→4560, 20→4561, 30→4562), outducts to neighbors' ports, `a scheme ipn 'ipnfw' 'ipnadminep'`, endpoints ipn:N.0–N.2. **ipnrc:** `a plan 20 udp/127.0.0.1:4561` etc. Copy the amroc.* style from testbed_recipe.md.

**The experiment:**

```bash
# start all 3 nodes (each: cd nX && ionadmin node.ionrc && ionadmin global.ionrc \
#   && ionsecadmin node.ionsecrc && bpadmin node.bprc && cd ..)
(cd n30 && stdbuf -oL bpsink ipn:30.1 > ground_rx.log 2>&1 &)
sleep 15   # inside the 10->20 window
(cd n10 && bpsource ipn:30.1 "science packet 001" -t 3600)   # TTL 1 h — must outlive the gap!
sleep 10
(cd n20 && bplist | grep -c "\*\*\*\* Bundle")   # EXPECT: 1  ← bundle parked at relay
sleep 80   # wait for 20->30 window (+90)
cat n30/ground_rx.log                             # EXPECT: payload delivered
```

**Success criteria:** bplist shows the bundle held at n20 during the gap; ground receives it after +90 s. **Record this terminal session** — 20 seconds of it belongs in the video ("the bundle waits at the relay because Earth isn't visible yet — this is DTN working as designed").

Gotchas: TTL must exceed the gap (`-t 3600`); default 300 s is fine here but set it explicitly — dawn-flush runs need hours. If nothing forwards at +90, check `ion.log` at n20 and confirm reverse contacts exist.

## M3 — Topology generator (Days 4–6)

**Goal:** a Python script `genscenario.py` that emits the full ~17-node scenario from a JSON description, so you can regenerate everything in seconds.

```json
{ "nodes": [
    {"id": 101, "type": "probe",  "battery_wh": 50,  "region": "farside"},
    {"id": 20,  "type": "relay",  "orbit": "queqiao24h", "buffer_mb": 50},
    {"id": 30,  "type": "ground", "region": "earth"} ],
  "period_s": 3600, "scale": "1s_real = 60s_sim" }
```

The generator writes: per-node config dirs (ports 4600+id, unique wm/sdr keys), `global.ionrc` with periodic visibility windows, and a `start_all.sh` / `stop_all.sh`.

**Visibility model — keep it simple and say so:** periodic windows approximating the geometry (far-side probes see relay R2 for X min per orbit period; R2 sees Earth Y min per period, offset; South Pole nodes see ELFO relay R1 on its 12-h cycle). Compress time: 1 real second = 1 sim minute, so a 14-day lunar night ≈ 5.6 h → compress further to minutes for demo runs. State the simplification in the video — judges respect explicit assumptions; LNIS-class rates (kbps proximity, higher DTE) keep numbers defensible.

**Scale check first:** before generating 17 nodes, test 6. Each ION node spawns ~10 processes; 17 nodes ≈ 170 processes. On WSL with 8 GB this should hold (reduce heapWords per node if memory is tight — except the relay, which needs a big SDR). If 17 won't run, 10–12 nodes (4 probes instead of 6, drop a rover) tells the same story.

## M4 — Traffic + measurement harness (Days 7–9)

**Goal:** `run_experiment.py` that starts topology, drives traffic, samples state, and emits CSVs.

- **Traffic:** per-node sender loops calling `bpsource ipn:30.1 "<node>:<seq>:<timestamp>"` with per-class TTL. Encode metadata in payload — the ground log then contains everything needed for per-bundle latency and delivery accounting. For volume, ION's `bpdriver`/`bpcounter` benchmark pair exists, but payload-tagged bpsource gives you per-bundle traceability; start there.
- **Priority:** ION supports class-of-service; `bptrace` sends with explicit priority (0=bulk, 1=std, 2=expedited). Use bptrace for the critical-telemetry class.
- **Relay buffer sampling:** every 5 s, `(cd n20 && bplist | grep -c "**** Bundle") >> buffer_occupancy.csv` with timestamp.
- **Drops:** cap the relay SDR (small `heapWords`, e.g. enough for ~100 bundles) so overload physically overflows; grep `ion.log` for no-space/abandoned events → drop counter. Calibrate the cap so baseline dawn-flush drops ~20–40% — visible but not silly.
- **Outputs:** `bundles.csv` (id, src, class, t_sent, t_delivered|DROPPED|EXPIRED), `buffer.csv`, `events.log`.

Definitions (locked in problem_specification.md): delivery ratio = delivered-before-TTL / generated; buffer overflow rate = storage drops / bundles handled at relay.

## M5 — Dawn-flush baseline (Days 10–12) ★ the pivotal experiment

**Scenario script:** 6 far-side probes "asleep" (no contacts) for the compressed night; at dawn T0, all six get contact windows to R2 simultaneously and each dumps its backlog (e.g., 50 bundles × 64 KB). R2's Earth downlink volume per window < aggregate inflow. Also inject a continuous low-rate critical-telemetry stream (bptrace priority 2) from one probe.

**Run vanilla SABR. Expected result (this is the demo's dramatic beat):** R2 buffer occupancy climbs to the cap → overflow drops begin → delivery ratio collapses; check whether critical telemetry survives (it may not — that's a finding).

**Produce two plots (matplotlib):**
1. R2 buffer occupancy vs time, with the SDR cap as a red line — the "flood" visual.
2. Delivery ratio by traffic class, baseline bar chart.

If baseline does NOT break: shrink R2's downlink windows or SDR cap, grow the backlog. You control the physics; the point is a *representative* stress, honestly parameterized.

## M6 — LunaFlow v0 controller (Days 13–16)

**Goal:** a Python daemon (`lunaflow_controller.py`) implementing the two policies through standard admin interfaces — no ION source changes:

1. **Congestion policy (staggered admission):** controller knows the contact plan + per-probe backlog + R2 capacity. At dawn it *reshapes* probe→R2 contact windows via `ionadmin` (staggered starts, per-contact rates matched to R2's drain rate) so aggregate inflow ≤ downlink capacity + headroom. Bundles queue at the *probes* (which have their own storage and just woke with full batteries) instead of overflowing R2.
2. **Energy policy:** an energy model harness tracks per-node battery (drain per byte sent, solar recharge when "lit"). When a node crosses its battery floor, the controller deletes its TX contacts (node keeps receiving nothing — it's asleep) *and* re-routes around it ahead of time; vanilla comparison run lets SABR route into the dead node and strand bundles.
3. **Priority protection:** reserve a slice of every R2→Earth window (a parallel low-rate contact entry) so priority-2 telemetry always has capacity.

This IS LunaFlow as proposed: energy- and congestion-aware policy governing a standards-compliant BPv7/SABR network — deployed exactly as your Phase 1 answer 7 says (admin at ground, policy over relays/terminals).

**A/B run:** same topology, same traffic traces, same seeds — controller off (baseline) vs on. Target headline: overflow drops near zero, delivery ratio up double digits, critical class ≈ 100%.

## M7 — Final runs and figures (Days 17–18)

- ≥5 seeded runs per arm (vary backlog sizes, window jitter). Mean ± range.
- Final figures: (1) buffer occupancy A/B overlay, (2) delivery ratio by class A/B bars, (3) drops timeline A/B, (4) optional: J/MB per probe from the energy model.
- Freeze code + configs in a git repo (public GitHub = credibility; link it in the submission).

## Video (Days 19–21) — 3:00 cut

| Time | Beat | Visual |
|---|---|---|
| 0:00–0:20 | Hook: "41% of the Moon can never call Earth. And once a month, the network drowns." | Moon graphic, dawn-flush animation (simple slides) |
| 0:20–0:55 | Problem: far side, 14-day night, dawn flush; energy causes congestion | Diagram of your topology |
| 0:55–1:25 | "I built it": ION testbed, real NASA flight software | Terminal montage: nodes starting, M2 bundle waiting at relay |
| 1:25–2:15 | The experiment: baseline collapse → LunaFlow A/B | The two money plots, animated in |
| 2:15–2:45 | Viasat fit: Moonlight roles ↔ LunaFlow tiers; commercial meaning of goodput | Simple mapping graphic |
| 2:45–3:00 | Roadmap (thesis, learned policies, federation) + close | You on camera |

Record terminals with large fonts (`asciinema` or plain screen record). Your voice, your face at open/close — Phase 3 judges will meet you in person; let Phase 2 preview that person.

---

## WSL notes

- Slow `make` is normal on WSL (file I/O). Build inside the Linux filesystem (`~/`, NOT `/mnt/c/...`) — this alone is often a 5–10× build speedup.
- ION's README flags a WSL2 networking quirk — everything here uses 127.0.0.1 only, which is unaffected.
- `killm` kills every node on the host; between runs also `rm -f ion_nodes` and check `ipcs -m` for leaked shared memory (`ipcrm` if needed).
- The NASA DTN dev-kit materials you found (slides + lab videos) map well onto M2 — do their 2-node LTP lab once; LTP instead of UDP is the flight-realistic convergence layer and a nice upgrade later if time allows.
