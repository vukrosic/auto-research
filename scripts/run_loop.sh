#!/usr/bin/env bash
# Automated dispatch-collect loop for explore experiments.
# Picks next pending experiment, dispatches, waits, collects, repeats.
# Usage: scripts/run_loop.sh [max_experiments]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="parameter-golf"
GPU="novita-rtx3090"
SNAPSHOTS="$AUTORESEARCH_DIR/experiments/$PROJECT/snapshots"
MAX_RUNS="${1:-999}"
POLL_INTERVAL=60  # seconds between completion checks
RESULTS_LOG="$AUTORESEARCH_DIR/reports/loop_results.jsonl"

mkdir -p "$(dirname "$RESULTS_LOG")"

run_count=0

while [ "$run_count" -lt "$MAX_RUNS" ]; do
    # Find next pending experiment (sorted by name for deterministic order)
    # Picks explore_ first, then validate_, then full_
    NEXT=""
    for d in "$SNAPSHOTS"/explore_*/status "$SNAPSHOTS"/validate_*/status "$SNAPSHOTS"/full_*/status; do
        [ -f "$d" ] || continue
        status=$(cat "$d")
        if [ "$status" = "pending" ]; then
            name=$(basename "$(dirname "$d")")
            NEXT="$name"
            break
        fi
    done

    if [ -z "$NEXT" ]; then
        echo "[$(date -u +%H:%M:%S)] No pending experiments. Loop done."
        break
    fi

    echo ""
    echo "========================================"
    echo "[$(date -u +%H:%M:%S)] DISPATCHING: $NEXT (run $((run_count+1))/$MAX_RUNS)"
    echo "========================================"

    # Dispatch
    if ! bash "$SCRIPT_DIR/dispatch.sh" "$PROJECT" "$NEXT" "$GPU"; then
        echo "[$(date -u +%H:%M:%S)] ERROR: dispatch failed for $NEXT, skipping"
        echo "failed" > "$SNAPSHOTS/$NEXT/status"
        continue
    fi

    # Poll for completion
    echo "[$(date -u +%H:%M:%S)] Waiting for $NEXT to complete..."
    start_time=$(date +%s)
    timeout=3600  # 1 hour max per experiment

    while true; do
        elapsed=$(( $(date +%s) - start_time ))
        if [ "$elapsed" -gt "$timeout" ]; then
            echo "[$(date -u +%H:%M:%S)] TIMEOUT: $NEXT exceeded ${timeout}s, marking failed"
            echo "failed" > "$SNAPSHOTS/$NEXT/status"
            break
        fi

        # Check if process is still running on GPU
        check_output=$(bash "$SCRIPT_DIR/check_experiment.sh" "$PROJECT" "$NEXT" 2>&1 || true)
        check_status=$(echo "$check_output" | head -1)
        if [ "$check_status" != "running" ]; then
            echo "[$(date -u +%H:%M:%S)] $NEXT appears done (${elapsed}s elapsed)"
            sleep 5  # brief settle time

            # Collect results
            if bash "$SCRIPT_DIR/collect_result.sh" "$PROJECT" "$NEXT" 2>&1; then
                # Log result
                if [ -f "$SNAPSHOTS/$NEXT/result.json" ]; then
                    val_bpb=$(python3 -c "import json; print(json.load(open('$SNAPSHOTS/$NEXT/result.json')).get('val_bpb', 'N/A'))")
                    echo "[$(date -u +%H:%M:%S)] RESULT: $NEXT = $val_bpb BPB (${elapsed}s)"
                    # Append to JSONL log
                    python3 -c "
import json, datetime
r = json.load(open('$SNAPSHOTS/$NEXT/result.json'))
r['_loop_collected_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
r['_experiment'] = '$NEXT'
with open('$RESULTS_LOG', 'a') as f:
    f.write(json.dumps(r) + '\n')
"
                else
                    echo "[$(date -u +%H:%M:%S)] WARNING: No result.json for $NEXT"
                fi
            else
                echo "[$(date -u +%H:%M:%S)] WARNING: collect failed for $NEXT"
            fi
            break
        fi

        sleep "$POLL_INTERVAL"
    done

    run_count=$((run_count + 1))
done

echo ""
echo "========================================"
echo "Loop finished: $run_count experiments completed"
echo "Results log: $RESULTS_LOG"
echo "========================================"
