#!/bin/bash
# Auto-pull results from all GPUs on a set interval.
# Runs in the background — start once, leave it running.
#
# Usage:
#   infra/auto_pull.sh              # pull every 2 min (default)
#   infra/auto_pull.sh 5            # pull every 5 min
#   nohup infra/auto_pull.sh > /tmp/auto_pull.log 2>&1 &   # detached

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INTERVAL="${1:-2}"   # minutes
LOG="/tmp/auto_pull.log"

if [[ -t 1 ]]; then
    GREEN=$'\033[32m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
    GREEN=""; YELLOW=""; CYAN=""; BOLD=""; DIM=""; RESET=""
fi

echo "${BOLD}Auto-pull started${RESET} — every ${INTERVAL}min — log: ${DIM}${LOG}${RESET}"
echo "Stop with: kill \$\$  or  pkill -f auto_pull.sh"
echo ""

while true; do
    TS=$(date '+%H:%M:%S')
    OUTPUT=$("$SCRIPT_DIR/pull_results.sh" 2>&1)

    # Count new results pulled
    NEW=$(echo "$OUTPUT" | grep -oP '\+\K[0-9]+(?= new)' | awk '{s+=$1}END{print s+0}')

    if [[ "$NEW" -gt 0 ]]; then
        echo "${GREEN}[${TS}] +${NEW} new results pulled${RESET}"
        # Log detail on new pulls
        echo "$OUTPUT" | grep -v "already pulled\|no results" | sed "s/^/  /" >> "$LOG"
    else
        echo "${DIM}[${TS}] no new results${RESET}"
    fi

    echo "[${TS}] pull run" >> "$LOG"
    echo "$OUTPUT" >> "$LOG"

    sleep $((INTERVAL * 60))
done
