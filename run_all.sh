#!/bin/bash
# Run every scheme we can on the CCmatic comparison link, in one test.py
# invocation (so one data dir, one metadata file): 1 flow, 30 s, 3 runs,
#   mm-delay 30 mm-link 12mbps.trace 12mbps.trace
#   --uplink-queue=droptail --uplink-queue-args=bytes=45000
#
# Usage: ./run_all.sh [DATA_DIR]          (default: results/all)
#   SCHEMES="cc_qdel vegas_r" ./run_all.sh   # override the scheme list
#   VEGAS_R=3 ./run_all.sh                   # queue target for vegas_r
#                                            # (default: R in src/config.yml)
# Needs each scheme set up first (src/wrappers/<scheme>.py setup). Not
# included: verus (does not build against Boost 1.74), webrtc and quic (need
# chromium-scale builds). Built-in vegas is added only if the kernel allows it.
set -e
cd "$(dirname "$0")"
DATA_DIR=${1:-results/all}

DEFAULT_SCHEMES="cubic bbr copa ledbat pcc pcc_experimental vivace sprout \
fillp fillp_sheep indigo taova scream"
CCMATIC_SCHEMES="cc_qdel cc_probe_fast cc_probe_drain cc_probe_slow cc_probe_qdel"
if grep -qw vegas /proc/sys/net/ipv4/tcp_allowed_congestion_control; then
  DEFAULT_SCHEMES="$DEFAULT_SCHEMES vegas"
fi
SCHEMES=${SCHEMES:-"$DEFAULT_SCHEMES $CCMATIC_SCHEMES vegas_r"}

python2 src/experiments/test.py local \
  --schemes "$SCHEMES" \
  -f 1 -t 30 --run-times 3 --data-dir "$DATA_DIR" \
  --uplink-trace src/experiments/12mbps.trace \
  --downlink-trace src/experiments/12mbps.trace \
  --prepend-mm-cmds "mm-delay 30" \
  --extra-mm-link-args "--uplink-queue=droptail --uplink-queue-args=bytes=45000"

echo "Analyse: python2 merge_results.py $DATA_DIR --out ${DATA_DIR}_report --published"
