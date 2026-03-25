#!/usr/bin/env bash
# Run the current base at each stage's step count to establish reference metrics.
# Canonical usage: scripts/calibrate_baselines.sh <project_name> <gpu_name> [stage]
# Legacy one-project shorthand: scripts/calibrate_baselines.sh <gpu_name> [stage]
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

if [ $# -ge 2 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="${1:?Usage: scripts/calibrate_baselines.sh <project_name> <gpu_name> [stage]}"
    GPU="${2:?Usage: scripts/calibrate_baselines.sh <project_name> <gpu_name> [stage]}"
    ONLY_STAGE="${3:-}"
else
    PROJECT="$(default_project_name "$AUTORESEARCH_DIR")"
    GPU="${1:?Usage: scripts/calibrate_baselines.sh <project_name> <gpu_name> [stage]}"
    ONLY_STAGE="${2:-}"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" calibrate "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Calibrate hook is not executable: $HOOK"
        exit 1
    fi
    if [ -n "$ONLY_STAGE" ]; then
        exec "$HOOK" "$PROJECT" "$GPU" "$ONLY_STAGE"
    else
        exec "$HOOK" "$PROJECT" "$GPU"
    fi
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"
REMOTE_DIR=$(project_remote_dir "$PROJECT_JSON" "$GPU")
BEST_FILE="$PROJECT_EXPERIMENTS/current_best.json"
RUN_COMMAND=$(project_field "$PROJECT_JSON" run_command)

# Read project stages
STAGES_JSON=$(python3 -c "
import json
project = json.load(open('$PROJECT_JSON'))
print(json.dumps(project.get('stages', {})))
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
    echo "All stage baselines already calibrated. Use scripts/calibrate_baselines.sh $PROJECT <gpu> <stage> to force recalibration."
    exit 0
fi

# Sync base code to GPU
echo "=== Syncing base to $GPU ==="
gpu_rsync_to "$GPU" "$PROJECT_EXPERIMENTS/base/" "$REMOTE_DIR/"

for entry in $STAGES_TO_RUN; do
    STAGE="${entry%%:*}"
    STEPS="${entry##*:}"
    RUN_NAME="$(project_json_get "$PROJECT_JSON" "stage_baseline_runs.$STAGE" "calibrate_${STAGE}")"

    echo ""
    echo "=== Calibrating stage '$STAGE' at $STEPS steps on $GPU ==="

    # Build the run command from project config template
    EXPANDED_CMD=$(echo "$RUN_COMMAND" | sed "s/{name}/$RUN_NAME/g; s/{steps}/$STEPS/g")

    mkdir -p "/tmp/calibrate_${STAGE}"
    # Run training synchronously
    gpu_ssh "$GPU" "cd $REMOTE_DIR && $EXPANDED_CMD" 2>&1 | tee "/tmp/calibrate_${STAGE}/command.log" | tail -30

    # Pull results
    LOG_PATH=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
print(p.get('log_path', 'logs/{name}.txt').replace('{name}', '$RUN_NAME'))
")
    RESULT_DIR_TEMPLATE=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
print(p.get('result_dir', 'results/{name}/').replace('{name}', '$RUN_NAME'))
")

    gpu_rsync_from "$GPU" "${REMOTE_DIR}/${LOG_PATH}" "/tmp/calibrate_${STAGE}/train.log" 2>/dev/null || true
    gpu_rsync_from "$GPU" "${REMOTE_DIR}/${RESULT_DIR_TEMPLATE}" "/tmp/calibrate_${STAGE}/results/" 2>/dev/null || true

    # Parse metrics using project config
    python3 -c "
import json, re
from pathlib import Path

log_path = Path('/tmp/calibrate_${STAGE}/train.log')
if not log_path.exists():
    fallback = Path('/tmp/calibrate_${STAGE}/command.log')
    if fallback.exists():
        log_path = fallback
summary_path = Path('/tmp/calibrate_${STAGE}/results/summary.json')
project = json.load(open('$PROJECT_JSON'))
metric_parse = project.get('metric_parse', {})
primary_metric = project.get('metric', 'val_bpb')
secondary_metrics = project.get('secondary_metrics', [])
all_metrics = [primary_metric] + secondary_metrics

if not log_path.exists():
    print('ERROR: No training log for stage $STAGE')
    exit(1)

text = log_path.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines()

summary = {}
if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
    except Exception:
        pass

parsed = {}
for metric_name in all_metrics:
    mconf = metric_parse.get(metric_name, {})
    value = None
    sjk = mconf.get('summary_json_key', '')
    if sjk and isinstance(summary, dict):
        obj = summary
        for part in sjk.split('.'):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is not None:
            try:
                value = float(obj)
            except (ValueError, TypeError):
                pass
    if value is None:
        regex = mconf.get('log_regex')
        if regex:
            for line in reversed(lines):
                m = re.search(regex, line)
                if m:
                    value = float(m.group(1))
                    break
    if value is not None:
        parsed[metric_name] = value

if primary_metric not in parsed:
    print(f'ERROR: Could not parse {primary_metric} for stage $STAGE')
    exit(1)

# Update current_best.json
best = json.load(open('$BEST_FILE'))
baselines = best.get('stage_baselines', {})
baseline_entry = {
    'steps': $STEPS,
    'calibrated_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'gpu': '$GPU',
}
baseline_entry.update(parsed)
baselines['$STAGE'] = baseline_entry
best['stage_baselines'] = baselines
with open('$BEST_FILE', 'w') as f:
    json.dump(best, f, indent=2)

print(f'Stage $STAGE calibrated: {parsed} at $STEPS steps')
"
done

echo ""
echo "=== Calibration complete ==="
cat "$BEST_FILE"
