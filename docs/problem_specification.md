# Problem Specification — Energy-Aware, Congestion-Managed DTN Routing for a Cislunar Relay Network

Scope locked (8 Aug 2026): sub-problems = **energy-aware routing + congestion management**; baseline = **vanilla SABR in ION**; primary metrics = **delivery ratio, buffer overflow rate**; deployment target = **relay spacecraft + user terminals, with admin control at the ground segment**; scenario = **South Pole + far-side hybrid, circa 2030–2032**.

---

## 1. Reference Scenario (the world we are solving for)

**Timeframe:** 2030–2032 — after Moonlight initial capability (end-2028) and NSN lunar relay deployment, during Artemis surface operations.

**Surface assets (~14 nodes):**

| Node class | Count | Location | Power profile | Traffic |
|---|---|---|---|---|
| Crewed base / habitat | 1 | Shackleton rim (South Pole) | Grid-class (kW, near-continuous solar on rim) | High-rate: voice/video (priority), ops telemetry |
| CLPS/commercial landers | 3 | South Pole region | Solar + battery; may die at night | Science bulk + telemetry |
| Rovers | 3 | South Pole region, terrain-masked routinely | Battery, ~10–50 W TX budget | Telemetry (periodic), science bursts |
| Far-side science station (e.g., radio astronomy in RF-quiet zone) | 1 | Far side (~Apollo crater region) | Solar + battery, 14-day night hibernation | Large bulk science, delay-tolerant |
| Far-side sensor/probe network | 6 | Distributed far side | Severely constrained (single-digit W) | Small periodic readings, long TTL |

**Relay constellation (2–3 nodes), modeled on flown/funded precedents:**

- **R1 — ELFO relay** (Lunar Pathfinder-style elliptical lunar frozen orbit, ~12 h period, apolune over South Pole): long dwell over polar assets, periodic Earth visibility.
- **R2 — far-side relay** (Queqiao-2-style 24 h frozen orbit, apolune over far side): the only Earth bridge for far-side nodes.
- **R3 (optional stress variable) — second ELFO or halo relay** with crosslinks to R1/R2, to study parallel-path routing.

**Ground segment (2–3 stations):** Earth stations (e.g., Viasat Real-Time Earth-class), each with scheduled visibility of R1/R2; weather-induced contact failures allowed. Admin/control plane lives here: contact plan generation, policy distribution, priority configuration.

**Network graph:** ~17–20 nodes. Every far-side bundle takes ≥2 hops (node → R2 → Earth, or node → R2 → R1 → Earth). No far-side node ever has a direct Earth link — by physics, not by assumption.

## 2. Formal Problem Statement

Given:
- A **contact plan** C = {(tx node, rx node, t_start, t_end, rate, confidence)} derived from orbital geometry — contacts are *scheduled*, not discovered.
- Per-node **buffer capacities** B_i (relay SSR sizes; small buffers on probes).
- Per-node **energy state** E_i(t): battery capacity, solar recharge profile (zero during 14-day night / eclipse), TX cost per byte (J/MB, rate-dependent), plus baseline load.
- A **traffic model**: bundle generation per node with (size, priority ∈ {critical, ops, bulk}, TTL).

Find a **bundle forwarding + scheduling policy** at each node that maximizes **delivery ratio** (bundles delivered before TTL expiry ÷ bundles generated), subject to:
- contact volume limits (rate × duration per contact),
- buffer limits B_i (secondary metric: **buffer overflow rate** = bundles dropped for storage ÷ bundles handled),
- energy budgets (a node with empty battery misses its *planned* contacts — invalidating the plan others route on),
- priority inversion constraints (critical traffic must not starve behind bulk).

This is multi-commodity flow over a time-expanded graph with node storage and energy capacities — NP-hard in general; practical policies must be heuristic and run on rad-tolerant flight processors.

## 3. Where Vanilla SABR Does Not Jointly Address Our Two Metrics

SABR (CCSDS 734.3-B-1; implemented as CGR in ION) computes earliest-arrival routes via Dijkstra over the contact graph, with volume booking on the **first hop only**. It performs well for the scheduled, single-agency, point-to-point mission profiles it was designed for; the limitations below arise when it is applied to a heterogeneous multi-node cislunar relay network.

**Congestion-related limitations → both metrics:**
1. **No downstream volume awareness.** SABR books capacity on the next contact but not along the whole path → many nodes route into the same "fast" relay contact → R2's buffer fills during far-side night backlogs → **overflow drops**.
2. **No backpressure/admission control.** Sources keep injecting regardless of relay buffer state; ION's congestion forecast is a ground-operator alarm, not an autonomous control loop.
3. **Parallel-path blindness.** Documented SABR weakness: overlooks parallel channels (R3/crosslinks idle while R2 saturates) → avoidable congestion → TTL expiries → **delivery ratio loss**.
4. **Priority handling is coarse.** Under overflow, drops are not policy-optimal; bulk science can crowd out ops telemetry.

**Energy-related limitations → delivery ratio, then plan integrity:**
5. **Energy-blind route choice.** SABR optimizes arrival time only. It will route through a battery-critical rover during lunar night if that's "fastest," draining it.
6. **Cascading plan invalidation.** When an energy-dead node misses planned contacts, every route computed through it silently fails; bundles strand until re-forwarding — TTL expiries cluster. This couples the energy problem *into* the routing problem: energy is not an add-on constraint, it is a contact-plan-truthfulness problem.
7. **No J/MB accounting.** Retransmissions after failed/overbooked contacts burn the scarcest resource (surface node energy) with zero visibility.

**The gap, one sentence:** CGR/SABR does not jointly address the multidimensional routing problem — contact-plan truthfulness, buffer occupancy, and node energy simultaneously — emerging in heterogeneous cislunar relay networks; the far side in lunar night stresses all three dimensions at once, precisely when relay demand peaks (backlogged science flushing at dawn).

## 4. Stress Events the Scenario Must Include (test matrix)

1. **Lunar dawn flush:** far-side nodes wake after 14-day night with full buffers → synchronized surge into R2 → the canonical congestion event.
2. **Relay outage:** R2 safe-mode for N hours (contact plan wrong) → tests uncertainty handling + rerouting via R1/R3.
3. **Ground station weather loss:** downlink contact fails → relay buffers grow → tests admission control.
4. **Rover terrain masking:** unscheduled loss of proximity contacts → tests re-forwarding cost in energy.
5. **Priority mix under overload:** verify critical telemetry delivery ratio stays ~100% while bulk degrades gracefully.

## 5. Success Criteria & Measurement Protocol

- **Primary:** vs vanilla SABR/ION on identical contact plans + traffic: higher delivery ratio (esp. under events 1–3) and lower buffer overflow rate. Target headline: measurable improvement on the dawn-flush event (e.g., X% fewer drops at R2).
- **Secondary (if time allows):** J/MB delivered per surface node; latency CDF per priority class; count of surface-node battery-depletion events.
- **Method:** containerized ION (or ion-core) nodes, contact plans scripted from simplified orbital geometry; external test harness enforces energy model (throttles/kills a node's contacts when battery ≤ 0) and logs bundle events. Baseline run vs modified-policy run, N seeds, same traffic traces. HDTN optional for relay nodes if ION throughput becomes the bottleneck.
- All runnable on one laptop — sized for a solo entrant by the Phase 2 deadline (27 Sep 2026).

## 6. Deployment Model (per your answer to Q5)

- **Relays (R1–R3):** run the enhanced forwarding/scheduling policy onboard — congestion state is local and time-critical; 2.6 s RTT rules out ground-in-the-loop reactions.
- **User terminals (Viasat's Moonlight scope):** energy-aware admission + priority marking at the source; report battery state in a small header extension so relays can route around energy-critical nodes.
- **Ground segment (admin control):** generates contact plans, sets policy parameters (priority weights, buffer thresholds, energy floors), monitors congestion forecasts, and can override — autonomy executes, ground governs. This maps 1:1 to Viasat's contracted roles: Moonlight network design (relay software), lunar user terminals, Earth ground infrastructure.

## 7. Assumptions & Non-Goals

**Assumed:** BPv7/LNIS compliance (interop preserved); contact plans available with confidence values; simplified link model (fixed rate per contact, no PHY modeling); single-provider network (multi-provider federation explicitly out of scope for Phase 1, mentionable as roadmap).
**Non-goals:** new hardware, PHY/RF design, PNT services, security hardening (acknowledge as roadblocks in Q5 of the submission), flight-qualified code.

## 8. Known Unknowns (to resolve during solution design)

1. Exact enhancement mechanism: energy/congestion-weighted route cost vs backpressure signaling vs learned policy (AI-in-space angle) vs hybrid — pick after baseline profiling shows *where* drops actually occur.
2. Realistic parameter values: relay buffer sizes, proximity link rates (LNIS S-band class), rover energy budgets — pull from LNIS + Lunar Pathfinder + Queqiao-2 public specs.
3. ION's exact drop behavior when SDR storage saturates (verify empirically, don't assume).
4. Whether contact "confidence" in ION can carry energy-derived probability, or whether a custom field is needed.
