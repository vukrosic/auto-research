#!/usr/bin/env bash
# Remove old experiment snapshots that are in terminal states.
# Usage: scripts/cleanup_snapshots.sh [--dry-run]
#
# Deletes snapshots with status: failed, rejected, promoted
# Keeps: pending, running, done, validated_winner, stale_winner
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SNAPSHOTS="$AUTORESEARCH_DIR/experiments/snapshots"

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
fi

TERMINAL_STATUSES="failed rejected promoted rollback_invalidated"
DELETED=0
KEPT=0

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

echo ""
echo "Summary: ${DELETED} deleted, ${KEPT} kept"
if [ "$DRY_RUN" = true ]; then
    echo "(dry run — nothing was actually deleted)"
fi
