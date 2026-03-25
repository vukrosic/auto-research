#!/usr/bin/env bash
# Create a new experiment snapshot from base.
# Canonical usage: scripts/new_experiment.sh <project_name> <experiment_name>
# Legacy one-project shorthand: scripts/new_experiment.sh <experiment_name>
set -euo pipefail

AUTORESEARCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$AUTORESEARCH_DIR/scripts/gpu_config.sh"

if [ $# -ge 2 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="$1"
    NAME="${2:?Usage: scripts/new_experiment.sh <project_name> <experiment_name>}"
else
    NAME="${1:?Usage: scripts/new_experiment.sh <project_name> <experiment_name>}"
    PROJECT="$(default_project_name "$AUTORESEARCH_DIR")"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" new_experiment "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: New-experiment hook is not executable: $HOOK"
        exit 1
    fi
    exec "$HOOK" "$PROJECT" "$NAME"
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"
SNAPSHOT_DIR="$PROJECT_EXPERIMENTS/snapshots/$NAME"

if [ -d "$SNAPSHOT_DIR" ]; then
    echo "ERROR: Experiment '$NAME' already exists at $SNAPSHOT_DIR"
    exit 1
fi

if [ ! -d "$PROJECT_EXPERIMENTS/base" ]; then
    echo "ERROR: No base directory for project '$PROJECT'. Run scripts/init_base.sh $PROJECT first."
    exit 1
fi

echo "Creating experiment snapshot: $NAME (project: $PROJECT)"
mkdir -p "$SNAPSHOT_DIR"

# Copy base repo
cp -r "$PROJECT_EXPERIMENTS/base" "$SNAPSHOT_DIR/code"

# Create or derive a stable base id for stale-winner detection
BASE_ID_FILE="$PROJECT_EXPERIMENTS/base_id.txt"
if [ -f "$BASE_ID_FILE" ]; then
    PARENT_BASE="$(cat "$BASE_ID_FILE")"
else
    PARENT_BASE="$(python3 -c "import json; b=json.load(open('$PROJECT_EXPERIMENTS/current_best.json')); print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")")"
    printf '%s\n' "$PARENT_BASE" > "$BASE_ID_FILE"
fi

# Infer stage from the experiment name prefix
STAGE="${NAME%%_*}"
if [ "$STAGE" = "$NAME" ]; then
    STAGE="explore"
fi
if ! python3 -c "
import json, sys
project = json.load(open('$PROJECT_JSON'))
sys.exit(0 if '$STAGE' in project.get('stages', {}) else 1)
"; then
    STAGE="explore"
fi

GOAL_NAME="${AUTORESEARCH_GOAL:-}"

# Pre-fill required metadata so unattended tooling has a valid starting point.
python3 -c "
import json, datetime

best = json.load(open('$PROJECT_EXPERIMENTS/current_best.json'))
project = json.load(open('$PROJECT_JSON'))

stages = project.get('stages', {})
stage_conf = stages.get('$STAGE', {})
steps = stage_conf.get('steps', 500)
threshold = stage_conf.get('threshold', 0.01)

# Use stage-specific baseline if available, otherwise fall back to full-run metric
stage_baselines = best.get('stage_baselines', {})
metric = project.get('metric', 'val_bpb')
if '$STAGE' in stage_baselines:
    baseline = stage_baselines['$STAGE']
    metric_val = baseline.get(metric) or baseline.get('val_bpb_quant') or baseline.get('val_bpb')
else:
    # Fallback: full-run metric (will be wrong for short stages — run calibrate_baselines first!)
    metric_val = best.get('val_bpb_quant') or best.get('val_bpb') or best.get(metric)

meta = {
    'name': '$NAME',
    'project': '$PROJECT',
    'hypothesis': '',
    'parent_base': '$PARENT_BASE',
    'stage': '$STAGE',
    'steps': steps,
    'priority': 1,
    'created_at': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'gpu': None,
    'baseline_metric': metric_val,
    'promotion_threshold': threshold,
    'env_overrides': {},
    'changes_summary': '',
    'owner': 'autonomous_lab'
}
if '$GOAL_NAME':
    meta['goal'] = '$GOAL_NAME'
with open('$SNAPSHOT_DIR/meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
"

# Create initial status
echo "pending" > "$SNAPSHOT_DIR/status"

echo "Snapshot created at: $SNAPSHOT_DIR/code/"
echo "Edit code and complete meta.json before dispatch."
