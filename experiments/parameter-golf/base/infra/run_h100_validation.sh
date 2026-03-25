#!/bin/bash
# Cross-hardware validation runs for 8xH100
# Run this on the H100 machine BEFORE any tuned submission
set -e
cd "$(dirname "$0")/.."

echo "========================================"
echo "Phase H2: 8xH100 Baseline Validation"
echo "========================================"

# H2a: Step-matched 500-step run (compare directly with the legacy baseline_500)
echo ""
echo "--- H2a: 500 steps, step-based schedule ---"
RUN_ID=h2_baseline_500 ITERATIONS=500 VAL_LOSS_EVERY=50 TRAIN_LOG_EVERY=100 \
  CHECKPOINT_EVERY=500 MAX_WALLCLOCK_SECONDS=0 \
  torchrun --nproc_per_node=8 train_gpt.py

echo ""
echo "--- H2b: Full 600s wall-clock run ---"
RUN_ID=h2_baseline_600s MAX_WALLCLOCK_SECONDS=600 VAL_LOSS_EVERY=500 \
  TRAIN_LOG_EVERY=200 \
  torchrun --nproc_per_node=8 train_gpt.py

echo ""
echo "========================================"
echo "H100 validation runs complete."
echo ""
echo "Next steps:"
echo "  1. Compare: bash infra/compare_hardware.sh logs/baseline_500.txt logs/h2_baseline_500.txt"
echo "  2. Check step count in h2_baseline_600s (expect ~13,780)"
echo "  3. Check warmdown timing in h2_baseline_600s log"
echo "========================================"
