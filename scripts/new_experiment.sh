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

# Create initial status
echo "pending" > "$SNAPSHOT_DIR/status"

echo "Snapshot created at: $SNAPSHOT_DIR/code/"
echo "Edit the code, then write meta.json and dispatch."
