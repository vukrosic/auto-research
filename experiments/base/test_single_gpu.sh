#!/bin/bash
# Quick parameter-golf test on single RTX 3090
# ~5 min run to verify baseline works

export RUN_ID="pg_rtx3090_baseline_$(date +%s)"
export ITERATIONS=500
export TRAIN_BATCH_TOKENS=65536
export VAL_BATCH_SIZE=262144
export VAL_LOSS_EVERY=50
export TRAIN_LOG_EVERY=25
export MAX_WALLCLOCK_SECONDS=600

echo "=== Parameter Golf — RTX 3090 Test Run ==="
echo "RUN_ID: $RUN_ID"
echo "Iterations: $ITERATIONS"
echo "Batch: $TRAIN_BATCH_TOKENS tokens/step"
echo "Time limit: ${MAX_WALLCLOCK_SECONDS}s"
echo "========================================="

cd /root/parameter-golf
python3 train_gpt.py 2>&1 | tee logs/${RUN_ID}.log

# Extract final metrics
echo ""
echo "=== RESULTS ==="
grep "val_bpb\|final" logs/${RUN_ID}.log | tail -5
