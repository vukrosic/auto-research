#!/usr/bin/env bash
# Initialize the base directory from an existing repo.
# Usage: scripts/init_base.sh <repo_path>
set -euo pipefail

AUTORESEARCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${1:?Usage: scripts/init_base.sh <path_to_repo>}"

if [ ! -d "$REPO" ]; then
    echo "ERROR: Repo not found at $REPO"
    exit 1
fi

echo "Initializing base from: $REPO"
mkdir -p "$AUTORESEARCH_DIR/experiments"

# Copy repo, excluding git and caches
rsync -a --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'logs/' --exclude '.claude/' \
    "$REPO/" "$AUTORESEARCH_DIR/experiments/base/"

echo "Base initialized at: $AUTORESEARCH_DIR/experiments/base/"
echo "Files: $(find "$AUTORESEARCH_DIR/experiments/base" -type f | wc -l)"
