#!/usr/bin/env bash
# Run a batch of experiments sequentially.
# Usage: infra/sweep.sh <sweep_file>
#
# Sweep file format (one experiment per line):
#   <name> <steps> <ENV_VAR=value> [ENV_VAR=value ...]
#
# Example sweep file:
#   p1_mlr_0.02 500 MATRIX_LR=0.02
#   p1_mlr_0.04 500 MATRIX_LR=0.04
#   p1_mlr_0.08 500 MATRIX_LR=0.08
#
# Lines starting with # are comments. Blank lines are skipped.

set -euo pipefail
cd "$(dirname "$0")/.."

SWEEP_FILE="${1:?Usage: infra/sweep.sh <sweep_file>}"

if [ ! -f "$SWEEP_FILE" ]; then
    echo "Error: sweep file not found: $SWEEP_FILE"
    exit 1
fi

TOTAL=$(grep -cvE '^\s*(#|$)' "$SWEEP_FILE" || true)
COUNT=0

echo "============================================"
echo "Parameter Golf Sweep: ${SWEEP_FILE}"
echo "Total experiments: ${TOTAL}"
echo "============================================"

while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue

    # Parse: name steps [env vars...]
    read -ra parts <<< "$line"
    NAME="${parts[0]}"
    STEPS="${parts[1]}"

    COUNT=$((COUNT + 1))
    echo ""
    echo ">>> [$COUNT/$TOTAL] $NAME ($STEPS steps)"

    # Export env vars from remaining parts
    for ((i=2; i<${#parts[@]}; i++)); do
        export "${parts[$i]}"
    done

    # Run experiment
    infra/run_experiment.sh "$NAME" "$STEPS"

    # Unset env vars to avoid leaking between experiments
    for ((i=2; i<${#parts[@]}; i++)); do
        varname="${parts[$i]%%=*}"
        unset "$varname"
    done

done < "$SWEEP_FILE"

echo ""
echo "============================================"
echo "Sweep complete. Analyzing results..."
echo "============================================"
echo ""

# Show comparison
python3 infra/analyze.py logs/$(head -1 "$SWEEP_FILE" | awk '{print $1}').txt \
    $(grep -vE '^\s*(#|$)' "$SWEEP_FILE" | awk '{print "logs/"$1".txt"}' | tr '\n' ' ') \
    2>/dev/null || python3 infra/analyze.py
