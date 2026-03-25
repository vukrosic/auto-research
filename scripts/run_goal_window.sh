#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

GOAL="${1:?Usage: scripts/run_goal_window.sh <goal> [interval_seconds]}"
INTERVAL="${2:-60}"
GOAL_JSON="$AUTORESEARCH_DIR/goals/$GOAL/goal.json"

if [ ! -f "$GOAL_JSON" ]; then
    echo "ERROR: Missing goal config: $GOAL_JSON" >&2
    exit 1
fi

REPORT_LABEL="$(python3 "$SCRIPT_DIR/goal_timing.py" report-iso "$GOAL_JSON")"
if [ "$REPORT_LABEL" = "none" ]; then
    REPORT_LABEL="pending first dispatch"
fi
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] goal runner started for $GOAL until $REPORT_LABEL"

while true; do
    NOW_EPOCH="$(date -u +%s)"
    REPORT_EPOCH="$(python3 "$SCRIPT_DIR/goal_timing.py" report-epoch "$GOAL_JSON")"
    if [ "$REPORT_EPOCH" != "none" ] && [ "$NOW_EPOCH" -ge "$REPORT_EPOCH" ]; then
        break
    fi

    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] materialize"
    python3 "$SCRIPT_DIR/materialize_goal_queue.py" "$GOAL" --limit 1 || true

    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cycle"
    python3 "$SCRIPT_DIR/autonomous_lab.py" cycle || true

    NOW_EPOCH="$(date -u +%s)"
    REPORT_EPOCH="$(python3 "$SCRIPT_DIR/goal_timing.py" report-epoch "$GOAL_JSON")"
    if [ "$REPORT_EPOCH" = "none" ]; then
        sleep "$INTERVAL"
        continue
    fi
    REMAINING="$(( REPORT_EPOCH - NOW_EPOCH ))"
    if [ "$REMAINING" -le 0 ]; then
        break
    fi
    if [ "$REMAINING" -lt "$INTERVAL" ]; then
        sleep "$REMAINING"
    else
        sleep "$INTERVAL"
    fi
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] final cycle"
python3 "$SCRIPT_DIR/autonomous_lab.py" cycle || true
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] report"
python3 "$SCRIPT_DIR/generate_goal_report.py" "$GOAL" || true
