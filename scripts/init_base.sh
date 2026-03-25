#!/usr/bin/env bash
# Initialize the base directory from an existing repo.
# Canonical usage: scripts/init_base.sh <project_name> [repo_path]
# Legacy one-project shorthand: scripts/init_base.sh <repo_path>
#
# If repo_path is omitted, reads it from projects/<project_name>.json
set -euo pipefail

AUTORESEARCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$AUTORESEARCH_DIR/scripts/gpu_config.sh"

if [ $# -ge 1 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="${1:?Usage: scripts/init_base.sh <project_name> [repo_path]}"
    REPO_OVERRIDE="${2:-}"
else
    PROJECT="$(default_project_name "$AUTORESEARCH_DIR")"
    REPO_OVERRIDE="${1:-}"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"

if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" init_base "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Init-base hook is not executable: $HOOK"
        exit 1
    fi
    if [ -n "$REPO_OVERRIDE" ]; then
        exec "$HOOK" "$PROJECT" "$REPO_OVERRIDE"
    else
        exec "$HOOK" "$PROJECT"
    fi
fi

REPO="${REPO_OVERRIDE:-$(project_field "$PROJECT_JSON" repo_path)}"

if [ ! -d "$REPO" ]; then
    echo "ERROR: Repo not found at $REPO"
    exit 1
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"

echo "Initializing base for project '$PROJECT' from: $REPO"
mkdir -p "$PROJECT_EXPERIMENTS"

# Copy repo, excluding git and caches
rsync -a --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'logs/' --exclude '.claude/' \
    "$REPO/" "$PROJECT_EXPERIMENTS/base/"

echo "Base initialized at: $PROJECT_EXPERIMENTS/base/"
echo "Files: $(find "$PROJECT_EXPERIMENTS/base" -type f | wc -l)"
