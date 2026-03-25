#!/usr/bin/env bash
# Promote a winning experiment to become the new base.
# Usage: scripts/promote.sh <experiment_name>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NAME="${1:?Usage: scripts/promote.sh <experiment_name>}"
SNAPSHOT_DIR="$AUTORESEARCH_DIR/experiments/snapshots/$NAME"

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

BASE_ID_FILE="$AUTORESEARCH_DIR/experiments/base_id.txt"
CURRENT_BASE_ID="$(if [ -f "$BASE_ID_FILE" ]; then cat "$BASE_ID_FILE"; else python3 -c "import json; b=json.load(open('$AUTORESEARCH_DIR/experiments/current_best.json')); print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")"; fi)"
PARENT_BASE="$(python3 -c "import json; print(json.load(open('$SNAPSHOT_DIR/meta.json')).get('parent_base',''))")"
if [ "$PARENT_BASE" != "$CURRENT_BASE_ID" ]; then
    echo "ERROR: parent_base mismatch. Snapshot is stale and must be revalidated."
    exit 1
fi

echo "=== Promoting $NAME to base ==="

# Backup current base
if [ -d "$AUTORESEARCH_DIR/experiments/base" ]; then
    BACKUP="$AUTORESEARCH_DIR/experiments/base_backup_$(date +%Y%m%d_%H%M%S)"
    mv "$AUTORESEARCH_DIR/experiments/base" "$BACKUP"
    echo "Old base backed up to: $BACKUP"
fi

# Copy winner to base
cp -r "$SNAPSHOT_DIR/code" "$AUTORESEARCH_DIR/experiments/base"

# Update current_best.json
python3 -c "
import json, datetime
result = json.load(open('$SNAPSHOT_DIR/result.json'))
meta = json.load(open('$SNAPSHOT_DIR/meta.json'))
best = {
    'experiment_name': '$NAME',
    'val_bpb': result.get('val_bpb'),
    'val_bpb_quant': result.get('val_bpb_quant'),
    'promoted_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'hypothesis': meta.get('hypothesis', ''),
    'parent_base': meta.get('parent_base'),
    'stage_baselines': {},  # must recalibrate after promotion
}
with open('$AUTORESEARCH_DIR/experiments/current_best.json', 'w') as f:
    json.dump(best, f, indent=2)
print(json.dumps(best, indent=2))
"

# Update base id and mark promoted
python3 -c "
import json
b = json.load(open('$AUTORESEARCH_DIR/experiments/current_best.json'))
print(f\"base::{b.get('experiment_name','unknown')}::{b.get('promoted_at','unknown')}\")
" > "$BASE_ID_FILE"
echo "promoted" > "$SNAPSHOT_DIR/status"

echo "=== $NAME is now the base ==="
