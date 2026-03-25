#!/usr/bin/env bash
# Promote a winning experiment to become the new base.
# Canonical usage: scripts/promote.sh <project_name> <experiment_name>
# Legacy one-project shorthand: scripts/promote.sh <experiment_name>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

if [ $# -ge 2 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="$1"
    NAME="${2:?Usage: scripts/promote.sh <project_name> <experiment_name>}"
else
    NAME="${1:?Usage: scripts/promote.sh <project_name> <experiment_name>}"
    PROJECT="$(snapshot_project_by_name "$AUTORESEARCH_DIR" "$NAME")"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" promote "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Promote hook is not executable: $HOOK"
        exit 1
    fi
    exec "$HOOK" "$PROJECT" "$NAME"
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"
SNAPSHOT_DIR="$PROJECT_EXPERIMENTS/snapshots/$NAME"

if [ ! -d "$SNAPSHOT_DIR/code" ]; then
    echo "ERROR: Experiment '$NAME' not found"
    exit 1
fi

if [ ! -f "$SNAPSHOT_DIR/result.json" ]; then
    echo "ERROR: No results for experiment '$NAME'"
    exit 1
fi

if [ ! -f "$SNAPSHOT_DIR/meta.json" ]; then
    echo "ERROR: No meta.json for experiment '$NAME'"
    exit 1
fi

STATUS="$(cat "$SNAPSHOT_DIR/status" 2>/dev/null || true)"
if [ "$STATUS" != "validated_winner" ]; then
    echo "ERROR: Experiment '$NAME' status is '$STATUS' (expected validated_winner)"
    exit 1
fi

BASE_ID_FILE="$PROJECT_EXPERIMENTS/base_id.txt"
CURRENT_BASE_ID="$(if [ -f "$BASE_ID_FILE" ]; then cat "$BASE_ID_FILE"; else python3 -c "import json; b=json.load(open('$PROJECT_EXPERIMENTS/current_best.json')); print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")"; fi)"
PARENT_BASE="$(python3 -c "import json; print(json.load(open('$SNAPSHOT_DIR/meta.json')).get('parent_base',''))")"
if [ "$PARENT_BASE" != "$CURRENT_BASE_ID" ]; then
    echo "ERROR: parent_base mismatch. Snapshot is stale and must be revalidated."
    exit 1
fi

echo "=== Promoting $NAME to base (project: $PROJECT) ==="

# Backup current base
if [ -d "$PROJECT_EXPERIMENTS/base" ]; then
    BACKUP="$PROJECT_EXPERIMENTS/base_backup_$(date +%Y%m%d_%H%M%S)"
    mv "$PROJECT_EXPERIMENTS/base" "$BACKUP"
    echo "Old base backed up to: $BACKUP"
fi

# Copy winner to base
cp -r "$SNAPSHOT_DIR/code" "$PROJECT_EXPERIMENTS/base"

# Update current_best.json
python3 -c "
import json, datetime
result = json.load(open('$SNAPSHOT_DIR/result.json'))
meta = json.load(open('$SNAPSHOT_DIR/meta.json'))
project = json.load(open('$PROJECT_JSON'))
metric = project.get('metric', 'val_bpb')
secondary = project.get('secondary_metrics', [])

best = {
    'experiment_name': '$NAME',
    'promoted_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'hypothesis': meta.get('hypothesis', ''),
    'parent_base': meta.get('parent_base'),
    'stage_baselines': {},  # must recalibrate after promotion
}
# Add primary and secondary metrics
best[metric] = result.get(metric)
for sm in secondary:
    if result.get(sm) is not None:
        best[sm] = result.get(sm)
with open('$PROJECT_EXPERIMENTS/current_best.json', 'w') as f:
    json.dump(best, f, indent=2)
print(json.dumps(best, indent=2))
"

# Update base id and mark promoted
python3 -c "
import json
b = json.load(open('$PROJECT_EXPERIMENTS/current_best.json'))
print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")
" > "$BASE_ID_FILE"
echo "promoted" > "$SNAPSHOT_DIR/status"

echo "=== $NAME is now the base for project $PROJECT ==="
