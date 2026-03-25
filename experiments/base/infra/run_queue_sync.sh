#!/usr/bin/env bash
# Usage: infra/run_queue_sync.sh <queue_file> [gpu_label]
#
# Runs experiments from a queue file one at a time.
# After each experiment, commits results and pushes to git.
# Pulls latest from remote before each experiment to stay in sync.

set -euo pipefail
cd "$(dirname "$0")/.."

QUEUE_FILE="${1:?Usage: infra/run_queue_sync.sh <queue_file> [gpu_label]}"
GPU_LABEL="${2:-local}"

echo "=== Queue Runner (${GPU_LABEL}) ==="
echo "Queue: ${QUEUE_FILE}"
echo "Started: $(date)"
echo ""

while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Parse: name steps [ENV=val ...]
    read -r NAME STEPS REST <<< "$line"

    echo ""
    echo "========================================"
    echo "[${GPU_LABEL}] Starting: ${NAME} (${STEPS} steps)"
    echo "Time: $(date)"
    echo "========================================"

    # Pull latest (non-fatal if fails)
    git pull --rebase origin lab 2>/dev/null || true

    # Build env string
    ENV_CMD=""
    for pair in $REST; do
        if [[ "$pair" =~ ^[A-Z_]+=.+ ]]; then
            export "$pair"
            ENV_CMD="${ENV_CMD} ${pair}"
        fi
    done

    # Run experiment
    export RUN_ID="${NAME}"
    export ITERATIONS="${STEPS}"
    # Use step-based termination on the local benchmark machine
    WALLCLOCK=$(python3 -c "import math; print(math.ceil(${STEPS} * 3.0 * 1.25))")
    export MAX_WALLCLOCK_SECONDS="${WALLCLOCK}"
    export VAL_LOSS_EVERY="${VAL_LOSS_EVERY:-50}"
    export TRAIN_LOG_EVERY="${TRAIN_LOG_EVERY:-10}"
    export SEED="${SEED:-1337}"

    mkdir -p results/"${NAME}" logs

    echo "[${GPU_LABEL}] Running: RUN_ID=${NAME} ITERATIONS=${STEPS} ${ENV_CMD}"

    if python3 train_gpt.py 2>&1 | tee logs/"${NAME}.txt"; then
        echo "[${GPU_LABEL}] ${NAME} completed successfully"

        # Export artifacts
        if [ -f "logs/${NAME}.txt" ]; then
            cp "logs/${NAME}.txt" "results/${NAME}/train.log"
        fi
        python3 infra/export_experiment_artifacts.py \
            --run-id "${NAME}" \
            --log-path "logs/${NAME}.txt" \
            --output-dir "results/${NAME}" 2>/dev/null || true

        # Commit and push results
        git add "results/${NAME}/" 2>/dev/null || true
        git commit -m "results(${GPU_LABEL}): ${NAME} — ${STEPS} steps${ENV_CMD}" 2>/dev/null || true
        git push origin lab 2>/dev/null || true

        echo "[${GPU_LABEL}] ${NAME} results committed and pushed"
    else
        echo "[${GPU_LABEL}] ${NAME} FAILED (exit $?)"
        echo "$(date) | ${GPU_LABEL} | ${NAME} | FAILED" >> logs/failed_experiments.log
    fi

    # Unset env vars from this run
    for pair in $REST; do
        if [[ "$pair" =~ ^([A-Z_]+)=.+ ]]; then
            unset "${BASH_REMATCH[1]}" 2>/dev/null || true
        fi
    done

done < "${QUEUE_FILE}"

echo ""
echo "=== Queue complete (${GPU_LABEL}) ==="
echo "Finished: $(date)"
