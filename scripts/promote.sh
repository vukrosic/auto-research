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
meta = json.load(open('$SNAPSHOT_DIR/meta.json')) if __import__('os').path.exists('$SNAPSHOT_DIR/meta.json') else {}
best = {
    'experiment_name': '$NAME',
    'val_bpb': result.get('val_bpb'),
    'val_bpb_quant': result.get('val_bpb_quant'),
    'promoted_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'hypothesis': meta.get('hypothesis', ''),
}
with open('$AUTORESEARCH_DIR/experiments/current_best.json', 'w') as f:
    json.dump(best, f, indent=2)
print(json.dumps(best, indent=2))
"

# Mark as winner
echo "winner" > "$SNAPSHOT_DIR/status"

echo "=== $NAME is now the base ==="
