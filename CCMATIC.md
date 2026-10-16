# CCmatic Listing 2 policies in Pantheon

Schemes: `cc_qdel`, `cc_probe_fast`, `cc_probe_drain`, `cc_probe_slow`,
`cc_probe_qdel` (CCmatic, NSDI'24, Listing 2).

## Layout
- `third_party/ccmatic_genericCC`: the authors' fork
  ([108anup/genericCC](https://github.com/108anup/genericCC), branch `ccmatic`,
  pinned to `0fa1ba7`). Kept separate from `third_party/genericCC` (Copa).
- `src/wrappers/patches/ccmatic.patch`: adds `CcmaticPolicy` (one class, policy
  selectable) and a `cctype=ccmatic policy=<name>` sender option. Applied by
  `setup`.
- `src/wrappers/ccmatic.py`: shared wrapper; `cc_*.py` are one-line wrappers.
- `src/config.yml`: scheme registrations (five policies + `vegas_r`).
- `run_all.sh`: runs every runnable scheme on the comparison link in one go.
- `merge_results.py`: merges data dirs; with `--published` also CSV + scatter plot.

## Provenance of each policy
| Policy | Source |
|---|---|
| `cc_qdel` | authors' `FastConv` rule, run unchanged (`update_rate_cwnd_fast_conv`) |
| `cc_probe_slow` | authors' `SlowConv` (starts as `cc_qdel`, switches after 2 consecutive intervals with >10 segs lost, then probe/drain), unchanged |
| `cc_probe_fast`, `cc_probe_drain`, `cc_probe_qdel` | **not in the authors' code**; transcribed from Listing 2 on the authors' beliefs (`min_c`=C_L, `max_c`=C_U, `min_qdel`=qdel_L, `min_rtt`=R_m) |

## Flagged discrepancies / missing details
1. The three transcribed policies have no reference implementation to diff
   against. They use alpha_R = 1 MSS/R_m and the Listing 1 floor `max(rate, MSS/R_m)`.
2. The authors' `cc_qdel`/`cc_probe_slow` differ from Listing 2 text: the
   additive term and rate floor are 5 MSS/R_m (the paper says alpha = 5 MSS for
   the implementation of `cc_probe_slow_k`), the drain threshold is
   `bq_belief2 > 10 segs` instead of `qU > MSS`, and `cc_qdel` adds the 5 MSS/R_m
   term to `2*C_L`. Kept as authored, not "corrected".
3. All policies keep the authors' window cap `cwnd = 2*C_U*(R_m + D)` (D = R_m),
   which is not part of Listing 2.
4. Estimator/timeouts are the authors' (`slow_conv.cc`): beliefs timeout every
   12 R_m (paper: "e.g. every 10 R_m"); init C_L=5 segs/s, C_U=1e5 segs/s;
   rate updated once per R_m; R_m = minimum observed RTT. The paper's qdel_L
   uses D = R_m, matching `JITTER_MULTIPLIER = 1`.
5. `cc_probe_slow` is the base (k=1) variant (`cctype=slow_conv`), not
   `slow_conv_<k>` (`SlowConvManual`).
6. Pacing is the authors' modified busy-wait pacing in `ctcp.hh` (paper App. G);
   not independently verified here.
7. Runtime selection: `CcmaticPolicy::set_policy()` (C++) and the
   `policy=` sender argument. No Laya integration.

## Results (1 flow, 30 s, 3 runs; mm-delay 30, 12 Mbps, droptail 45000 B)
Mean over 3 runs (Pantheon `pantheon_perf.json`; tput Mbit/s, 95th-pct one-way delay ms, loss %; loss is Pantheon's `Loss rate`):

| Scheme | tput | delay | loss |
|---|---|---|---|
| cc_probe_fast | 9.98 | 61.01 | 9.64 |
| cc_probe_drain | 9.93 | 61.04 | 10.74 |
| cc_probe_qdel | 10.23 | 61.00 | 9.32 |
| cc_probe_slow | 8.23 | 61.11 | 4.32 |
| cc_qdel | **no valid result** (see below) | | |

**cc_qdel stalls.** In all 3 runs the flow stops delivering at ~7-11 s, so
Pantheon's analyzer discards them ("had duration ~7 s but should have been
around 30 s"; `cc_qdel` has an empty entry in `pantheon_perf.json`). Raw logs
are kept. Cause, reproduced with the authors' unmodified `cctype=fast_conv`:
the buffer (30 packets, ~30 ms) is below D = R_m, so qdel_L stays 0 and the rule
keeps sending 2*C_L (~2x capacity, ~50% loss). The authors' sender
(`ctcp.hh`) only sends while `seq_num < largest_ack + 1 + cwnd` and has no
RTO/retransmit, so when a window is lost it deadlocks. cc_qdel is designed for
deep buffers (Table 2, G1); not "fixed" here.

## Running everything, merging, CSV and plot
```
# one-time: build each scheme (src/wrappers/<scheme>.py setup); see notes below
./run_all.sh results/all                       # every runnable scheme, 1 flow, 30 s, 3 runs
python2 merge_results.py results/all --out results/all_report --published
```
- `run_all.sh` runs all schemes in one `test.py` invocation: Pantheon's
  defaults that build here (cubic, bbr, copa, ledbat, pcc, pcc_experimental,
  vivace, sprout, fillp, fillp_sheep, indigo, taova, scream), the five CCmatic
  policies and `vegas_r` (plus built-in `vegas` if the kernel allows it).
  `SCHEMES="..." ./run_all.sh` overrides the list.
- `merge_results.py DIR [DIR ...] --out OUT` merges separate data dirs (they
  must share link settings). With `--published [PERF_JSON_OR_URL]` it also runs
  Pantheon's `plot.py` on OUT (stock plots + `pantheon_perf.json`), writes
  `OUT/summary.csv` (per run: throughput, p95 delay, loss %) and
  `OUT/scatter_with_published.{pdf,svg,png}` (+ `_mean`), y axis fixed to the
  published graph's 0-12.56 Mbit/s. The default published source is Pantheon's
  emu-17 `perf.json`.
- Schemes with no valid local runs are drawn from the published data as
  **hollow "(published)" markers** (Muses variants, verus, quic, vegas where
  not run). Those come from a 2020 run on other hardware and are not directly
  comparable. The Muses code is not in upstream Pantheon and I found no public
  source. WebRTC has no published data. `cc_qdel` has no valid runs (stalls).
- `cc_probe_drain` and `cc_probe_fast` nearly coincide on the plot.

Build notes (done without root here):
- Copa's `sender`/`receiver` were built with `makepp CXXFLAGS=...` without
  `-Werror` (gcc 11 rejects the old code) and relinked with an rpath to a
  user-space jemalloc; makepp/jemalloc were extracted from `.deb`s.
- indigo uses user-space TensorFlow 1.14 (`pip2 install --user
  tensorflow==1.14.0`, needs the grpcio 1.26 wheel first).
- scream needs its nested `scream_upstream` submodule (`git submodule update`
  failed here; a manual clone at `c3370fd` worked).
- Not run: verus (does not compile against Boost 1.74: `milliseconds(double)`),
  vegas (kernel module needs root), webrtc and quic (chromium-scale builds).
  SCReAM's ~0.2 Mbit/s is what the scheme delivers here, not a plotting error.

## Reproduce (CCmatic policies only)
```
git submodule update --init third_party/ccmatic_genericCC third_party/pantheon-tunnel
src/experiments/setup.py --install-deps --schemes "cc_qdel"   # makepp, boost, protobuf, jemalloc (needs root)
src/experiments/setup.py --setup --schemes "cc_qdel cc_probe_fast cc_probe_drain cc_probe_slow cc_probe_qdel"
SCHEMES="cc_qdel cc_probe_fast cc_probe_drain cc_probe_slow cc_probe_qdel" ./run_all.sh results/ccmatic
src/analysis/analyze.py --data-dir results/ccmatic            # plots + pantheon_report.pdf
```
Run configuration: `mm-delay 30 mm-link 12mbps.trace 12mbps.trace
--uplink-queue=droptail --uplink-queue-args=bytes=45000`, 1 flow, 30 s.

## Vegas-R (`vegas_r`)
Separate scheme; built-in `vegas` is untouched. Implemented as `VegasR` in
`third_party/ccmatic_genericCC/vegas_r.{hh,cc}` (added by
`src/wrappers/patches/ccmatic.patch`, same sender as the CCmatic policies:
`cctype=vegas_r r_target=<R>`).

Rule, once per round (not per ACK): `if RTT - RTT_min > R*RTT/cwnd: cwnd =
max(2, cwnd-1) else cwnd += 1`. cwnd in packets, times in ms, `double`
arithmetic. RTT_min = minimum valid RTT of the connection; RTT = minimum valid
sample in the completed round. A sample is valid if it is finite and > 0 (RTT =
ACK arrival time - the packet's send timestamp).

- **R is required:** no default in the C++ (`r_target=` missing or not > 0 makes
  the sender exit). The wrapper reads `VEGAS_R` from the environment, else
  `R` under `vegas_r` in `src/config.yml` (set to 3 there for these runs; this
  value is my choice, not specified), and exits if not positive.
- **Round:** ends when the ACK of a packet sent after the round began arrives;
  that ACK's sample starts the next round. A round with no valid sample does
  not update cwnd (counts as skipped).
- **In-flight limit:** `window = cwnd`; the existing transport (`ctcp.hh`)
  sends only while `seq < largest_ack + 1 + window`. This counts packets sent
  after the highest ACK, so packets lost below it are not counted in flight.
  No pacing (inter-send time 0).
- **Startup:** cwnd starts at 2, no slow start; it just follows the rule
  (+1 per RTT).
- **Loss/timeout:** no reaction to loss beyond what the rule sees through RTT.
  The transport has no RTO and no retransmission, so if a whole window is lost
  and no ACK arrives the sender stalls permanently (same transport limitation
  that stalled cc_qdel). Not observed in the vegas_r runs.

Tests: `python2 tests/test_vegas_r.py` (builds and runs
`vegas_r_test.cc`: below / equal / above the threshold, cwnd floor, fractional
cwnd and R, required R, invalid samples skipped, exactly one update per RTT in
a window-limited simulation, queue settling near the target).

Run (same link): `SCHEMES="vegas_r" VEGAS_R=3 ./run_all.sh results/vegas_r`
(after `python2 src/wrappers/vegas_r.py setup`; applies the patch and builds).
**Built-in `vegas` could not be run locally** (needs the `tcp_vegas` kernel
module, which requires root), so the comparison uses Pantheon's published Vegas
result as a hollow marker: `python2 merge_results.py results/vegas_r --out
results/vegas_cmp --published` (published Vegas: ~11.9 Mbit/s, ~36.5 ms;
Vegas-R: ~11.2 Mbit/s, ~38 ms). On a machine with the module loaded, run
`SCHEMES="vegas vegas_r" ./run_all.sh` and use `src/analysis/analyze.py`.
