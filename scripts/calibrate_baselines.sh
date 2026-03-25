#!/usr/bin/env bash
# Run the current base at each stage's step count to establish reference metrics.
# Usage: scripts/calibrate_baselines.sh <gpu_name> [stage]
#
# If [stage] is given, only calibrate that stage. Otherwise calibrates all stages
# that don't already have a baseline.
#
# This is a blocking operation — it runs training synchronously and updates
# current_best.json with stage_baselines when done.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

GPU="${1:?Usage: scripts/calibrate_baselines.sh <gpu_name> [stage]}"
ONLY_STAGE="${2:-}"

REMOTE_DIR=$(gpu_var "$GPU" REMOTE_DIR)
BEST_FILE="$AUTORESEARCH_DIR/experiments/current_best.json"

# Read project stages
STAGES_JSON=$(python3 -c "
import json, glob
files = sorted(glob.glob('$AUTORESEARCH_DIR/projects/*.json'))
if files:
    project = json.load(open(files[0]))
    print(json.dumps(project.get('stages', {})))
else:
    print('{}')
")

# Get stages to calibrate
STAGES_TO_RUN=$(python3 -c "
import json
stages = json.loads('$STAGES_JSON')
best = json.load(open('$BEST_FILE'))
existing = best.get('stage_baselines', {})
only = '$ONLY_STAGE'
for name, conf in stages.items():
    if name == 'full':
        continue  # full-run metric is already in current_best
    if only and name != only:
        continue
    if name not in existing or only:
        print(f'{name}:{conf[\"steps\"]}')
")

if [ -z "$STAGES_TO_RUN" ]; then
    echo "All stage baselines already calibrated. Use scripts/calibrate_baselines.sh <gpu> <stage> to force recalibration."
    exit 0
fi

# Sync base code to GPU
echo "=== Syncing base to $GPU ==="
gpu_rsync_to "$GPU" "$AUTORESEARCH_DIR/experiments/base/" "$REMOTE_DIR/"

for entry in $STAGES_TO_RUN; do
    STAGE="${entry%%:*}"
    STEPS="${entry##*:}"
    RUN_NAME="calibrate_${STAGE}"

    echo ""
    echo "=== Calibrating stage '$STAGE' at $STEPS steps on $GPU ==="

    # Run training synchronously
    gpu_ssh "$GPU" "cd $REMOTE_DIR && bash infra/run_experiment.sh '$RUN_NAME' '$STEPS'" 2>&1 | tail -30

    # Pull results
    mkdir -p "/tmp/calibrate_${STAGE}"
    gpu_rsync_from "$GPU" "${REMOTE_DIR}/logs/${RUN_NAME}.txt" "/tmp/calibrate_${STAGE}/train.log" 2>/dev/null || true
    gpu_rsync_from "$GPU" "${REMOTE_DIR}/results/${RUN_NAME}/" "/tmp/calibrate_${STAGE}/results/" 2>/dev/null || true

    # Parse metrics
    python3 -c "
import json, re
from pathlib import Path

log_path = Path('/tmp/calibrate_${STAGE}/train.log')
summary_path = Path('/tmp/calibrate_${STAGE}/results/summary.json')

if not log_path.exists():
    print('ERROR: No training log for stage $STAGE')
    exit(1)

text = log_path.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines()

val_bpb = None
val_quant = None

if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        last_eval = summary.get('last_eval') or {}
        final_quant = summary.get('final_quant_eval') or {}
        val_bpb = last_eval.get('val_bpb')
        val_quant = final_quant.get('val_bpb')
    except Exception:
        pass

if val_bpb is None:
    for line in reversed(lines):
        m = re.search(r'\bval_bpb[:=]\s*([0-9]+(?:\.[0-9]+)?)\b', line)
        if m:
            val_bpb = float(m.group(1))
            break

if val_quant is None:
    for line in reversed(lines):
        m = re.search(r'final_int8_zlib_roundtrip_exact[^0-9]*([0-9]+(?:\.[0-9]+)?)', line)
        if m:
            val_quant = float(m.group(1))
            break

if val_bpb is None:
    print('ERROR: Could not parse val_bpb for stage $STAGE')
    exit(1)

# Update current_best.json
best = json.load(open('$BEST_FILE'))
baselines = best.get('stage_baselines', {})
baselines['$STAGE'] = {
    'val_bpb': val_bpb,
    'val_bpb_quant': val_quant,
    'steps': $STEPS,
    'calibrated_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'gpu': '$GPU',
}
best['stage_baselines'] = baselines
with open('$BEST_FILE', 'w') as f:
    json.dump(best, f, indent=2)

print(f'Stage $STAGE calibrated: val_bpb={val_bpb}, val_bpb_quant={val_quant} at $STEPS steps')
"
done

echo ""
echo "=== Calibration complete ==="
cat "$BEST_FILE"
