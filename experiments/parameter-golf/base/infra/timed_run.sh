#!/usr/bin/env bash
# Timed experiment runner.
# Probes actual step time, predicts duration, runs for exactly <target_seconds>.
#
# Usage: infra/timed_run.sh <name> <target_seconds> [ENV=val ...]
# Example: NUM_EXPERTS=4 infra/timed_run.sh moe4e_test 60
#
# Prints before starting: "⏱ Predicted: N steps × Xms/step = Y.Zs"
# Actual wall-clock runtime matches target_seconds closely.

set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${1:?Usage: infra/timed_run.sh <name> <target_seconds> [ENV=val ...]}"
TARGET_SEC="${2:?Usage: infra/timed_run.sh <name> <target_seconds>}"
shift 2

# Apply any extra env vars passed as KEY=val args
for kv in "$@"; do
    export "$kv"
done

PROBE_STEPS=5
PROBE_LOG="/tmp/probe_${NAME}_$$.txt"
OVERHEAD_SEC=5  # fixed overhead: final eval, log copy, artifact export

# ── Step 1: probe step time ──────────────────────────────────────────────────
echo "┌─ Probing step time for: ${NAME}"
echo "│  Config: $(env | grep -E '^(NUM_LAYERS|MODEL_DIM|NUM_EXPERTS|MLP_ACT|EMBED_BOTTLENECK|TRAIN_BATCH_TOKENS)=' | tr '\n' ' ')"

ITERATIONS=$PROBE_STEPS \
MAX_WALLCLOCK_SECONDS=120 \
VAL_LOSS_EVERY=99999 \
TRAIN_LOG_EVERY=1 \
RUN_ID="probe_${NAME}" \
python3 train_gpt.py 2>&1 > "$PROBE_LOG"

# Extract average step time (ms) from last logged step
STEP_AVG_MS=$(grep "step_avg:" "$PROBE_LOG" | tail -1 | grep -oP "step_avg:\K[\d.]+" || echo "")

if [ -z "$STEP_AVG_MS" ]; then
    echo "│  ⚠ Probe failed — falling back to GPU estimate"
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 | xargs || echo "")
    case "$GPU_NAME" in
        *3090*) STEP_AVG_MS=162 ;;
        *5090*) STEP_AVG_MS=80  ;;
        *H100*) STEP_AVG_MS=50  ;;
        *)      STEP_AVG_MS=200 ;;
    esac
fi

# ── Step 2: compute iterations ───────────────────────────────────────────────
USABLE_SEC=$(python3 -c "print(max(1, $TARGET_SEC - $OVERHEAD_SEC))")
STEPS=$(python3 -c "import math; print(max(10, math.floor($USABLE_SEC * 1000 / $STEP_AVG_MS)))")
PREDICTED_SEC=$(python3 -c "print(round($STEPS * $STEP_AVG_MS / 1000 + $OVERHEAD_SEC, 1))")

echo "│  Measured: ${STEP_AVG_MS}ms/step"
echo "└─ ⏱ Predicted: ${STEPS} steps × ${STEP_AVG_MS}ms = ${PREDICTED_SEC}s  (target: ${TARGET_SEC}s)"
echo ""

rm -f "$PROBE_LOG"

# Set warmup/warmdown to 10% of steps (min 5)
WARMUP_STEPS=$(python3 -c "print(max(5, int($STEPS * 0.1)))")
WARMDOWN_ITERS=$(python3 -c "print(max(5, int($STEPS * 0.15)))")

# ── Step 3: run actual experiment ────────────────────────────────────────────
export RUN_ID="${NAME}"
export ITERATIONS="${STEPS}"
export MAX_WALLCLOCK_SECONDS="${TARGET_SEC}"
export WARMUP_STEPS="${WARMUP_STEPS:-$WARMUP_STEPS}"
export WARMDOWN_ITERS="${WARMDOWN_ITERS:-$WARMDOWN_ITERS}"
export VAL_LOSS_EVERY="${VAL_LOSS_EVERY:-$(python3 -c "print(max(10, int($STEPS / 2)))")}"
export TRAIN_LOG_EVERY="${TRAIN_LOG_EVERY:-$(python3 -c "print(max(5, int($STEPS / 10)))")}"
export SEED="${SEED:-1337}"

mkdir -p "results/${NAME}" logs

T_START=$(date +%s)
python3 train_gpt.py 2>&1 | tee "logs/${NAME}.txt"
T_END=$(date +%s)
ACTUAL_SEC=$((T_END - T_START))

cp "logs/${NAME}.txt" "results/${NAME}/train.log" 2>/dev/null || true
python3 infra/export_experiment_artifacts.py \
    --run-id "${NAME}" \
    --log-path "logs/${NAME}.txt" \
    --output-dir "results/${NAME}" 2>/dev/null || true

echo ""
echo "=== Results for ${NAME} ==="
grep "val_bpb" "logs/${NAME}.txt" | grep -v "^step:0" | tail -1 || true
grep "final_int8_zlib_roundtrip_exact" "logs/${NAME}.txt" | tail -1 || true
echo "⏱ Actual wall-clock: ${ACTUAL_SEC}s (predicted: ${PREDICTED_SEC}s)"
echo "=========================="
