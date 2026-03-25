#!/usr/bin/env bash
# Create a new experiment snapshot from base.
# Usage: scripts/new_experiment.sh <experiment_name>
set -euo pipefail

AUTORESEARCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAME="${1:?Usage: scripts/new_experiment.sh <experiment_name>}"
SNAPSHOT_DIR="$AUTORESEARCH_DIR/experiments/snapshots/$NAME"

if [ -d "$SNAPSHOT_DIR" ]; then
    echo "ERROR: Experiment '$NAME' already exists at $SNAPSHOT_DIR"
    exit 1
fi

if [ ! -d "$AUTORESEARCH_DIR/experiments/base" ]; then
    echo "ERROR: No base directory. Run scripts/init_base.sh first."
    exit 1
fi

echo "Creating experiment snapshot: $NAME"
mkdir -p "$SNAPSHOT_DIR"

# Copy base repo
cp -r "$AUTORESEARCH_DIR/experiments/base" "$SNAPSHOT_DIR/code"

# Create or derive a stable base id for stale-winner detection
BASE_ID_FILE="$AUTORESEARCH_DIR/experiments/base_id.txt"
if [ -f "$BASE_ID_FILE" ]; then
    PARENT_BASE="$(cat "$BASE_ID_FILE")"
else
    PARENT_BASE="$(python3 -c "import json; b=json.load(open('$AUTORESEARCH_DIR/experiments/current_best.json')); print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")")"
    printf '%s\n' "$PARENT_BASE" > "$BASE_ID_FILE"
fi

# Infer stage from the experiment name prefix
STAGE="${NAME%%_*}"
if [ "$STAGE" = "$NAME" ]; then
    STAGE="explore"
fi
if ! printf '%s\n' "explore validate full" | tr ' ' '\n' | grep -qx "$STAGE"; then
    STAGE="explore"
fi

# Pre-fill required metadata so unattended tooling has a valid starting point.
python3 -c "
import json, datetime
best = json.load(open('$AUTORESEARCH_DIR/experiments/current_best.json'))

# Read project config for stage settings
import glob
project_files = sorted(glob.glob('$AUTORESEARCH_DIR/projects/*.json'))
project = json.load(open(project_files[0])) if project_files else {}
stages = project.get('stages', {})
stage_conf = stages.get('$STAGE', {})
steps = stage_conf.get('steps', 500)
threshold = stage_conf.get('threshold', 0.01)

# Use stage-specific baseline if available, otherwise fall back to full-run metric
stage_baselines = best.get('stage_baselines', {})
if '$STAGE' in stage_baselines:
    metric = stage_baselines['$STAGE'].get('val_bpb_quant') or stage_baselines['$STAGE'].get('val_bpb')
else:
    # Fallback: full-run metric (will be wrong for short stages — run calibrate_baselines first!)
    metric = best.get('val_bpb_quant') or best.get('val_bpb')

meta = {
    'name': '$NAME',
    'hypothesis': '',
    'parent_base': '$PARENT_BASE',
    'stage': '$STAGE',
    'steps': steps,
    'priority': 1,
    'created_at': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'gpu': None,
    'baseline_metric': metric,
    'promotion_threshold': threshold,
    'env_overrides': {},
    'changes_summary': '',
    'owner': 'autonomous_lab'
}
with open('$SNAPSHOT_DIR/meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
"

# Create initial status
echo "pending" > "$SNAPSHOT_DIR/status"

echo "Snapshot created at: $SNAPSHOT_DIR/code/"
echo "Edit code and complete meta.json before dispatch."
