#!/usr/bin/env bash
# Runs all experiments from queues/active.txt sequentially on 1x 3090.
# Skips already-completed experiments (those with results/<name>/train.log).
# If an experiment crashes, logs the error and continues to the next one.
set -uo pipefail
cd "$(dirname "$0")/.."

ACTIVE_QUEUE=$(readlink -f "queues/active.txt")
REQUESTED_QUEUE=$(readlink -f "${1:-queues/active.txt}")
if [ "$REQUESTED_QUEUE" != "$ACTIVE_QUEUE" ]; then
    echo "ERROR: only queues/active.txt may be executed." >&2
    echo "Copy any archived or proposed batch into queues/active.txt first." >&2
    exit 1
fi

QUEUE_FILE="queues/active.txt"
FAIL_LOG="logs/failed_experiments.log"

echo "===== Queue runner started at $(date) ====="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'unknown')"

count=0
skip=0
fail=0
done_count=0

while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// /}" ]] && continue

    # Parse: name steps [ENV=val ...]
    name=$(echo "$line" | awk '{print $1}')
    steps=$(echo "$line" | awk '{print $2}')
    # Extract env vars (fields 3+)
    envvars=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i}')

    # Skip if already done
    if [ -d "results/$name" ] && [ -f "results/$name/train.log" ]; then
        skip=$((skip + 1))
        continue
    fi

    count=$((count + 1))
    echo ""
    echo "============================================"
    echo "[$(date '+%H:%M:%S')] STARTING experiment $count: $name ($steps steps)"
    echo "  Env: $envvars"
    echo "============================================"

    # Build env prefix
    env_cmd=""
    for ev in $envvars; do
        # Strip any trailing comment
        [[ "$ev" =~ ^# ]] && break
        env_cmd="$env_cmd export $ev;"
    done

    # Run the experiment, capturing exit code
    start_time=$(date +%s)
    (
        eval "$env_cmd"
        bash infra/run_experiment.sh "$name" "$steps"
    )
    exit_code=$?
    end_time=$(date +%s)
    elapsed=$(( end_time - start_time ))

    if [ $exit_code -ne 0 ]; then
        fail=$((fail + 1))
        echo "[$(date '+%H:%M:%S')] FAILED: $name (exit=$exit_code, ${elapsed}s)"
        echo "$(date) | $name | exit=$exit_code | ${elapsed}s | $envvars" >> "$FAIL_LOG"
    else
        done_count=$((done_count + 1))
        echo "[$(date '+%H:%M:%S')] DONE: $name (${elapsed}s)"
    fi

    # Brief cooldown between experiments
    sleep 5

done < "$QUEUE_FILE"

echo ""
echo "===== Queue runner finished at $(date) ====="
echo "Completed: $done_count | Failed: $fail | Skipped (already done): $skip"
