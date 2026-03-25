#!/usr/bin/env bash
# Remove old experiment snapshots that are in terminal states.
# Usage: scripts/cleanup_snapshots.sh [project_name] [--dry-run]
#
# If project_name is given, only clean that project. Otherwise cleans all.
# Deletes snapshots with status: failed, rejected, promoted
# Keeps: pending, running, done, validated_winner, stale_winner
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DRY_RUN=false
PROJECT=""

for arg in "$@"; do
    if [ "$arg" = "--dry-run" ]; then
        DRY_RUN=true
    else
        PROJECT="$arg"
    fi
done

TERMINAL_STATUSES="failed rejected promoted rollback_invalidated"
DELETED=0
KEPT=0

# Determine which project dirs to scan
if [ -n "$PROJECT" ]; then
    PROJECT_DIRS="$AUTORESEARCH_DIR/experiments/$PROJECT"
    if [ ! -d "$PROJECT_DIRS/snapshots" ]; then
        echo "ERROR: No snapshots for project '$PROJECT'"
        exit 1
    fi
else
    PROJECT_DIRS=$(find "$AUTORESEARCH_DIR/experiments" -mindepth 1 -maxdepth 1 -type d)
fi

for proj_dir in $PROJECT_DIRS; do
    proj_name=$(basename "$proj_dir")
    SNAPSHOTS="$proj_dir/snapshots"
    [ -d "$SNAPSHOTS" ] || continue

    echo "=== Project: $proj_name ==="
    for snapshot in "$SNAPSHOTS"/*/; do
        [ -d "$snapshot" ] || continue
        name=$(basename "$snapshot")
        status=$(cat "$snapshot/status" 2>/dev/null || echo "unknown")

        if echo "$TERMINAL_STATUSES" | grep -qw "$status"; then
            if [ "$DRY_RUN" = true ]; then
                echo "WOULD DELETE: $name (status=$status)"
            else
                rm -rf "$snapshot"
                echo "DELETED: $name (status=$status)"
            fi
            DELETED=$((DELETED + 1))
        else
            echo "KEPT: $name (status=$status)"
            KEPT=$((KEPT + 1))
        fi
    done
done

echo ""
echo "Summary: ${DELETED} deleted, ${KEPT} kept"
if [ "$DRY_RUN" = true ]; then
    echo "(dry run — nothing was actually deleted)"
fi
