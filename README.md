# LunaFlow: Energy-Aware Routing for Delay-Tolerant Networks

*An energy-aware, congestion-managed policy layer for DTN (Bundle Protocol v7 / SABR), built and measured on NASA's open-source [ION-DTN](https://github.com/nasa-jpl/ION-DTN) stack.*

## The problem in 30 seconds

Delay-Tolerant Networks operate where continuous end-to-end connectivity does not exist: links come and go on a **schedule** (a contact plan), data moves by **store-and-forward** in self-contained bundles, and intermediate relays hold traffic — sometimes for hours — until the next contact opens. Many DTN nodes are also **energy-constrained**: they run on batteries, sleep through long outage periods, and pay a real energy cost per transmitted byte.

The standard routing algorithm for scheduled DTNs — Contact Graph Routing / Schedule-Aware Bundle Routing (CCSDS SABR, deployed in NASA flight software) — is proven, but it does not jointly address the multidimensional routing problem emerging in heterogeneous relay networks:

- **Congestion-blind:** capacity is booked on the first hop only; there is no backpressure and no path-wide volume awareness, so relays with finite storage overflow under load.
- **Energy-blind:** routes optimize delivery time only. SABR will happily route through a battery-critical node — and when that node dies, every planned contact through it silently fails, invalidating the contact plan other nodes route on.
- **The two are coupled:** in networks where nodes sleep through outages, the energy cycle *synchronizes* the load — all nodes wake with full buffers and flood the relay simultaneously (the **dawn-flush** pattern). Prior work treats energy (E-CGR [[6]](#references)) and congestion (load-balanced SABR [[7]](#references), capacity/buffer-constrained CGR [[8]](#references)) as separate extensions; the joint problem is open.

**LunaFlow** manages both jointly, as a policy layer on top of standard BPv7/SABR — no new hardware, no protocol fork. This repo builds it bottom-up and measures it against vanilla SABR on delivery ratio and buffer overflow rate.

The motivating deployment is cislunar relay networking (see [docs/cislunar_dtn_problem_brief.md](docs/cislunar_dtn_problem_brief.md)); the same mechanics apply to any scheduled, energy-constrained DTN — disaster-response networks, remote-area connectivity, underwater and airborne relays.

## Repository layout

```
docs/        milestone documentation (M1.md, M2.md, ...) + problem brief & formal spec
scripts/     scenario generators and experiment runners
scenarios/   generated node configurations per experiment
results/     CSVs and plots from measurement runs
```

## Quickstart

1. Build ION-DTN from source (no root needed) — see [docs/M1.md](docs/M1.md) §Build.
2. `./scripts/m2_setup.sh` — generates the 3-node store-and-forward scenario.
3. `export ION_NODE_LIST_DIR=$HOME/testbed/m2 && ./scripts/m2_run.sh` — runs the timed experiment (~2 min); expect `M2 PASS`.
4. `cd scripts && python3 genscenario.py ../scenarios/m4_smoke.json && python3 run_experiment.py ~/testbed/m4_smoke` — tagged traffic + measurement (~3 min); CSVs + `summary.json` land in `results/`.

## Milestones

| # | What it proves | Status |
|---|---|---|
| M1 | Two ION nodes exchange bundles over UDP (bping 3/3, ~4 ms RTT) | ✅ [docs/M1.md](docs/M1.md) |
| M2 | Store-and-forward across a 50 s coverage gap (bundle waits at relay) | ✅ [docs/M2.md](docs/M2.md) |
| M3 | Scenario generator: ~17-node relay topology from JSON | ✅ [docs/M3.md](docs/M3.md) |
| M4 | Traffic + measurement harness (delivery ratio, buffer occupancy → CSV); relay overflow on UDP kills the relay's induct | ✅ [docs/M4.md](docs/M4.md) |
| M5 | **Dawn-flush baseline: vanilla SABR under synchronized overload** | ⏳ |
| M6 | LunaFlow controller: joint energy + congestion policy via standard admin interfaces | ⏳ |
| M7 | A/B comparison, multi-seed runs, final plots | ⏳ |

## Key concepts (re-entry cheat sheet)

- **DTN / BPv7** ([RFC 9171](https://www.rfc-editor.org/rfc/rfc9171.html)): store-and-forward networking for links that are *scheduled to be down*. Data travels in self-contained "bundles" that wait at intermediate nodes until the next contact opens. Loss modes: TTL expiry and buffer overflow — not link drops.
- **Contact plan**: the schedule of who-can-talk-to-whom-when, loaded into every node (`a contact +10 +40 10 20 10000` = node 10→20, seconds 10–40, 10 kB/s). **This is where the scenario physics lives** — every outage, sleep cycle, and load surge is expressed as contact plan structure.
- **CGR/SABR**: routing over the time-expanded contact graph — a route is a sequence of *future* contacts, not currently-up links.
- **ION**: NASA JPL's flight implementation. One "node" = ~10 cooperating daemons around a shared-memory data store (SDR). `ionadmin` = node/contact plan config, `bpadmin` = bundle protocol config, `ipnadmin` = neighbor→address mapping, `killm` = nuclear teardown.
- **LunaFlow's bet**: energy and congestion are *causally coupled* in sleep-cycle DTNs, so they must be managed jointly — which no SABR extension currently does (closest prior art: E-CGR, Marchese & Patrone 2020 [[6]](#references) = energy only; Kamps et al. 2025 [[7]](#references) = congestion only).

## Standards context

Bundle Protocol v7 per [RFC 9171](https://www.rfc-editor.org/rfc/rfc9171.html) [[2]](#references) / CCSDS 734.2; routing per CCSDS 734.3 (SABR) [[3]](#references). LunaFlow operates through standard admin interfaces and BPv7 extension mechanisms, so enhanced and vanilla nodes stay interoperable.

## References

**DTN architecture and standards**

1. S. Burleigh, A. Hooke, L. Torgerson, K. Fall, V. Cerf, B. Durst, K. Scott, H. Weiss, "Delay-tolerant networking: an approach to interplanetary Internet," *IEEE Communications Magazine*, vol. 41, no. 6, pp. 128–136, 2003. [doi:10.1109/MCOM.2003.1204759](https://doi.org/10.1109/MCOM.2003.1204759)
2. S. Burleigh, K. Fall, E. Birrane, "Bundle Protocol Version 7," RFC 9171, IETF, 2022. [rfc-editor.org/rfc/rfc9171](https://www.rfc-editor.org/rfc/rfc9171.html)
3. CCSDS, "Schedule-Aware Bundle Routing," Recommended Standard CCSDS 734.3-B-1 (Blue Book), July 2019. [ccsds.org](https://ccsds.org/publications/bluebooks/entry/3167)

**Contact Graph Routing (the baseline)**

4. G. Araniti, N. Bezirgiannidis, E. Birrane, I. Bisio, S. Burleigh, C. Caini, M. Feldmann, M. Marchese, J. Segui, K. Suzuki, "Contact graph routing in DTN space networks: overview, enhancements and performance," *IEEE Communications Magazine*, vol. 53, no. 3, pp. 38–46, 2015. [doi:10.1109/MCOM.2015.7060480](https://doi.org/10.1109/MCOM.2015.7060480)
5. J. A. Fraire, O. De Jonckère, S. C. Burleigh, "Routing in the Space Internet: A contact graph routing tutorial," *Journal of Network and Computer Applications*, vol. 174, art. 102884, 2021. [doi:10.1016/j.jnca.2020.102884](https://doi.org/10.1016/j.jnca.2020.102884)

**Closest prior art (energy or congestion, separately)**

6. M. Marchese, F. Patrone, "E-CGR: Energy-Aware Contact Graph Routing Over Nanosatellite Networks," *IEEE Transactions on Green Communications and Networking*, vol. 4, no. 3, pp. 890–902, 2020. [doi:10.1109/TGCN.2020.2978296](https://doi.org/10.1109/TGCN.2020.2978296)
7. J. J. Kamps, F. Paluncic, B. T. J. Maharaj, "A load-balancing enhancement to schedule-aware bundle routing," *International Journal of Satellite Communications and Networking*, vol. 43, no. 2, pp. 122–130, 2025. [doi:10.1002/sat.1549](https://doi.org/10.1002/sat.1549)
8. T. Alhajj, V. Corlay, "Improved Contact Graph Routing in Delay Tolerant Networks with Capacity and Buffer Constraints," arXiv:2410.15546, 2024. [arxiv.org/abs/2410.15546](https://arxiv.org/abs/2410.15546)

Further background (cislunar programs, LunaNet, uncertain contact plans) is collected in [docs/cislunar_dtn_problem_brief.md](docs/cislunar_dtn_problem_brief.md) §2.

## License

Configs, scripts, and docs in this repo: MIT. ION-DTN is NASA JPL's open-source software under its own license — not vendored here.
