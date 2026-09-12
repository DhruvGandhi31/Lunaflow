# Cislunar DTN Routing & Lunar Far-Side Coverage — Deep Problem Brief

Prepared for: Viasat Space for Good Australia 2026, Phase 1 (deadline 23 Aug 2026)
Focus areas: #11 Lunar Communication (primary), #9 AI in Space, #4 Open Architecture (secondary)

---

## 1. The Problem in Extreme Detail

### 1.1 The physics that creates the problem

**Tidal locking.** The Moon rotates once per orbit, so the same hemisphere always faces Earth. The far side (~41% of the surface, plus libration zones) **never** has line-of-sight to Earth. No amount of transmit power fixes this — it is a geometry problem. Any far-side asset (lander, rover, radio telescope, sensor network) can only communicate via a **relay** (orbiting or surface-based).

**South pole terrain masking.** Artemis and most commercial landers target the lunar South Pole (water ice). There, Earth sits at ~0–6° elevation on the horizon; crater rims and terrain block direct-to-Earth (DTE) links for large fractions of time even on the near side. NASA explicitly cites the South Pole as a region "where direct communications with Earth can be difficult."

**Distance and delay.** Earth–Moon distance ≈ 384,400 km → one-way light time ~1.28 s, round-trip ~2.6 s. Add relay hops, processing, and store-and-forward waits, and interactive protocols (TCP) collapse: TCP throughput degrades severely with delay and any loss; handshakes and retransmission timers assume millisecond RTTs.

**Intermittency.** Relay satellites in lunar orbit have limited, scheduled visibility windows with (a) surface assets, (b) Earth ground stations, and (c) each other. Links are not "down" due to failure — disconnection is the *normal operating state*. The network is a time-varying graph of scheduled "contacts."

### 1.2 The environment that constrains any solution

- **Lunar night:** 14 Earth days of darkness. Solar-powered surface nodes must survive on batteries at −173 °C; many simply hibernate. Energy for communication is the scarcest resource on the surface.
- **Thermal swings:** roughly −173 °C to +127 °C between night and day.
- **Radiation:** no magnetosphere; electronics suffer single-event upsets; hardware must be rad-tolerant, which caps onboard compute (relevant if you propose AI onboard).
- **Severely energy-constrained surface nodes:** per the cislunar DTN literature, surface probes and relays "work in a severely energy-constrained environment, which limits their rate of data transmission." Every retransmission wasted is mission lifetime lost.
- **No maintenance:** a deployed relay cannot be repaired. Software robustness and graceful degradation are mandatory.

### 1.3 The networking state of the art — and its open gaps

**DTN (Delay/Disruption Tolerant Networking)** is the accepted answer to intermittency. Core idea: **store-and-forward at the bundle layer**. Data is wrapped in self-contained "bundles" (Bundle Protocol v7, IETF **RFC 9171**, profiled by CCSDS 734.2). Nodes hold bundles in persistent storage until the next scheduled contact, then forward hop-by-hop. No end-to-end path ever needs to exist at one moment.

**Contact Graph Routing (CGR)** is the standard DTN routing algorithm for space: since contacts are *scheduled* (orbits are predictable), each node holds a "contact plan" and computes routes over the time-expanded graph (the deployed refinement is CCSDS **Schedule-Aware Bundle Routing, SABR**).

**Documented open problems (this is the gap your concept attacks):**

1. **Scalability.** CGR route search over large contact graphs is expensive; multi-destination CGR is **NP-complete**. Works for a handful of nodes; the challenge brief itself anticipates "hundreds of institutional and commercial missions" in the next two decades. Nobody has demonstrated CGR at that scale.
2. **Congestion.** Congestion management "is an open research issue in DTN." SABR can overlook parallel channels and overload single contacts. Buffer overflow at a relay = dropped bundles = lost science data.
3. **Uncertain contact plans.** CGR assumes the schedule is truth. Real contacts fail (pointing errors, weather at ground stations, power safing). Routing under *probabilistic* contact plans is an active research frontier.
4. **Energy-blindness.** Standard CGR optimizes delivery time, not energy. For a battery-limited far-side node in lunar night, the energy-optimal route ≠ the fastest route. Energy-aware bundle scheduling is largely unsolved.
5. **Multi-provider routing.** LunaNet envisions NASA + ESA + JAXA + commercial relays as one federated network. Cross-provider routing, prioritization, and trust are defined only at the specification level; first interoperability tests are planned ~2029. (This is where focus area #4, Open Architecture, overlaps.)
6. **Coverage/topology design.** A single relay (the Queqiao model) cannot cover the whole far side + poles continuously. What constellation + surface-relay mix delivers coverage at minimum cost is an open design/optimization question.

### 1.4 What exists today (baseline you must know cold)

| Asset / Program | Status | Notes |
|---|---|---|
| **NASA DSN** | Operational, oversubscribed | Legacy DTE for deep space; cannot scale to hundreds of lunar users |
| **Queqiao-1 / Queqiao-2 (China)** | Operational | Only far-side relays ever flown. Queqiao-2: 4.2 m antenna, 24-h elliptical frozen orbit over Apollo crater, supports Chang'e-6/7/8. Proprietary, single-provider, not interoperable |
| **LunaNet / LNIS (NASA-ESA-JAXA)** | Specification (v5+) | Mandates BPv7 DTN, S/K-band proximity links, X/K DTE, LDPC coding, up to 200 Msps K-band. Interop tests ~2029 |
| **ESA Moonlight** | Funded (€176M for 3 yrs, Nov 2025) | Lunar Pathfinder relay from 2026; initial capability end-2028; full service 2030. **Telespazio prime; Viasat designs the comms network, Earth ground infrastructure, and lunar user terminals** |
| **NASA Near Space Network Services** | IDIQ, $4.82B ceiling | **Intuitive Machines**: lunar relay constellation (incl. South Pole support). **Viasat**: DTE ground/space relay services out to 2M km |
| **NASA CPNT architecture** | In definition | Umbrella comms/PNT architecture for cislunar |

**The one-sentence problem statement:** *The Moon is about to host hundreds of missions, and the far side and South Pole absolutely require an intermittent relay network — but CGR/SABR, proven as it is for today's scheduled point-to-point links, does not jointly address the multidimensional routing problem (scale, congestion, contact uncertainty, energy, multi-provider federation) emerging in heterogeneous cislunar relay networks during the 2026–2035 lunar buildout.*

---

## 2. Official Sources

**Standards & specifications**
- RFC 9171 — Bundle Protocol v7 (IETF): https://www.rfc-editor.org/rfc/rfc9171.html
- CCSDS BPv7 experimental spec (734.x): https://ccsds.org/wp-content/uploads/gravity_forms/5-448e85c647331d9cbaf66c096458bdd5/2025/06/734x20o1.pdf
- RFC 9174 — TCP Convergence Layer v4: https://datatracker.ietf.org/doc/html/rfc9174.txt
- NASA LunaNet Interoperability Specification: https://www.nasa.gov/directorates/somd/space-communications-navigation-program/lunanet-interoperability-specification/
- LunaNet overview (NASA Goddard): https://www.nasa.gov/centers-and-facilities/goddard/lunanet-empowering-artemis-with-communications-and-navigation-interoperability/

**Programs**
- ESA Moonlight press release: https://www.esa.int/Newsroom/Press_Releases/ESA_launches_Moonlight_to_establish_lunar_communications_and_navigation_infrastructure
- Viasat × Telespazio Moonlight role (Viasat official): https://www.viasat.com/news/latest-news/corporate/2025/to-the-moon-viasat-moonlight-telespazio/
- Telespazio announcement: https://www.telespazio.com/en/news-and-stories-detail/-/detail/viasat-lunar-orbiting-satellite-system-telespazio
- Viasat NSN contract (investor release): https://investors.viasat.com/news-releases/news-release-details/viasat-selected-48b-ceiling-nasa-near-space-network-services
- Intuitive Machines NSN lunar relay contract: https://investors.intuitivemachines.com/news-releases/news-release-details/nasa-awards-intuitive-machines-near-space-network-contract
- NASA lunar relay navigation delivery: https://www.nasa.gov/technology/space-comms/nasa-delivers-navigation-system-for-commercial-lunar-relay/
- Queqiao-2 (NASA NSSDCA): https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=QUEQIAO-2
- Queqiao-2 (Planetary Society): https://www.planetary.org/space-missions/queqiao-2-chinas-bridge-for-lunar-exploration

**Research (open problems)**
- Deeper dive into LunaNet interoperability, Schier 2026 (Wiley, IJSCN): https://onlinelibrary.wiley.com/doi/10.1002/sat.1531
- DTN performance in cislunar relay architecture (MDPI Sensors): https://www.mdpi.com/1424-8220/25/1/195
- DTN in cislunar space (SmallSat 2026): https://digitalcommons.usu.edu/smallsat/2026/all2026/42/
- Improved CGR (arXiv): https://arxiv.org/pdf/2410.15546
- Routing under uncertain contact plans (arXiv): https://arxiv.org/pdf/2108.07092
- Knowledge-centric communication for autonomous cislunar networks (arXiv): https://arxiv.org/html/2608.04817
- 6G cislunar communications survey (arXiv): https://arxiv.org/pdf/2407.16672
- TCP-based DTN in cislunar domain (PMC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11859326/

---

## 3. Open-Source Software Stacks

| Tool | Link | What it is |
|---|---|---|
| **ION-DTN** (NASA JPL) | https://github.com/nasa-jpl/ION-DTN | NASA's flight-proven DTN implementation (BPv7, LTP, CGR/SABR). C. The reference stack |
| **ion-core** (NASA JPL) | https://github.com/nasa-jpl/ion-core | Streamlined packaging of ION's core DTN features — easier entry point |
| **HDTN** (NASA Glenn) | https://github.com/nasa/HDTN | High-rate DTN, modern modular C++, built for high-throughput relay nodes — exactly the relay use case |
| **DTN7** | https://dtn7.github.io/ | Community BPv7 implementations (Go/Rust) — lighter for quick prototyping |
| **IPN-V** | https://arxiv.org/pdf/2409.04857 | Interplanetary Network Visualizer — simulation/visualization of DTN topologies |

All runnable on a laptop; ION and HDTN can be networked in containers to emulate a multi-node cislunar topology with scripted contact plans.

---

## 4. Why Solving This Matters — Technical Reasoning

1. **It unblocks the far side and South Pole.** Every high-value near-term lunar target (polar ice, far-side radio astronomy in the RF-quiet zone, Chang'e-class science) sits where DTE fails. Better relay routing is the *only* path to reliable data return from these regions.
2. **It converts scarce relay capacity into more science.** Relays are the bottleneck; smarter routing (congestion-aware, parallel-channel-aware) raises effective network goodput without launching new hardware — pure software leverage, the cheapest kind of space infrastructure.
3. **It extends surface asset lifetime.** Energy-aware bundle scheduling means a rover spends fewer joules per delivered megabyte — directly more mission per battery.
4. **It de-risks against contact failures.** Routing that models contact *uncertainty* keeps data flowing when schedules slip, instead of stranding bundles at dead ends.
5. **It's the missing autonomy layer.** With 2.6 s+ RTT and scheduled outages, ground-in-the-loop routing doesn't scale to hundreds of nodes. Autonomous, on-node route decisions (potentially learning-assisted — your AI-in-space angle) are a prerequisite for the "Internet-at-the-Moon" LunaNet describes.
6. **It's standards-aligned, not standards-competing.** Building on BPv7/SABR/LNIS means the work slots into LunaNet/Moonlight rather than fighting them — realistic path to adoption.

## 5. Why Solving This Matters — Business Reasoning

1. **The market is funded now, not hypothetical.** Two $4.82B-ceiling NASA NSN IDIQ contracts (Viasat DTE + Intuitive Machines lunar relay), ESA Moonlight €176M initial tranche, Artemis, CLPS, Chang'e-7/8 — the challenge brief itself cites "hundreds of institutional and commercial missions planned over the next two decades."
2. **Comms is the first commercial lunar utility.** Moonlight and NSN are explicitly *communications-as-a-service* models: missions buy connectivity instead of building bespoke radios + booking DSN time. Whoever routes traffic best sells the most capacity at the highest margin.
3. **Direct Viasat alignment (worth 15/100 rubric points).** Viasat is *designing Moonlight's communication network, ground infrastructure, and lunar user terminals* and holds NSN DTE services. A routing/network-management concept is a software layer Viasat could deploy on assets it is already contracted to build. Few Phase 1 entrants will have alignment this literal.
4. **Software margins on hardware programs.** A routing/QoS layer is IP that scales across every relay Viasat or partners fly — no marginal launch cost. It also enables tiered SLAs (priority for crewed Artemis traffic, bulk for science backhaul) = revenue segmentation.
5. **Multi-provider federation is a revenue feature.** LunaNet-style roaming between Viasat/Moonlight, Intuitive Machines, and agency assets needs exactly the cross-provider routing/accounting this problem contains — the entity providing that layer becomes the clearing house of the lunar network.
6. **Terrestrial spillover.** The same DTN techniques serve disaster-zone and remote-Australia connectivity (focus areas #3 and #8) — a "Space for Good" story: technology built for the Moon hardens networks for communities on Earth when infrastructure fails.

---

## 6. Where to Dive Next (open questions to resolve before designing a solution)

1. Which sub-problem to attack: energy-aware routing, congestion management, uncertainty-robust CGR, multi-provider federation, or constellation topology design? (Pick 1–2 max for a solo entry.)
2. What reference scenario: far-side science station? South Pole Artemis base? Mixed 20–50 node network circa 2032?
3. What baseline to beat: vanilla SABR in ION — by what metric (delivery ratio, latency, J/MB, buffer overflow rate)?
4. What can be demonstrated by Phase 2 (27 Sep): a containerized ION/HDTN testbed with scripted contact plans and a comparison plot is realistic solo.
5. How Viasat would deploy it: onboard Moonlight relays, in ground scheduling software, or in user terminals?
