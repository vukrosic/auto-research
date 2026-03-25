#!/usr/bin/env bash
# Timed queue runner. Queue format: <name> <target_seconds> [ENV=val ...]
# Each experiment runs for exactly target_seconds wall-clock time.
# Prints timing prediction before each run.
#
# Usage: infra/run_timed_queue.sh <queue_file>

set -uo pipefail
cd "$(dirname "$0")/.."

QUEUE_FILE="${1:-queues/active.txt}"

echo "===== Timed queue runner started at $(date) ====="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo 'unknown')"
echo ""

count=0; skip=0; fail=0

while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// /}" ]] && continue

    name=$(echo "$line" | awk '{print $1}')
    target_sec=$(echo "$line" | awk '{print $2}')
    envvars=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i}')

    # Skip already done
    if [ -d "results/$name" ] && [ -f "results/$name/train.log" ]; then
        echo "[SKIP] $name (already done)"
        skip=$((skip + 1))
        continue
    fi

    count=$((count + 1))
    echo "════════════════════════════════════════════"
    echo "[$(date '+%H:%M:%S')] Experiment $count: $name (target: ${target_sec}s)"
    echo "════════════════════════════════════════════"

    # Export env vars inline
    env_export=""
    for kv in $envvars; do
        env_export="$env_export $kv"
        export "${kv?}"
    done

    T0=$(date +%s)
    if bash infra/timed_run.sh "$name" "$target_sec" $envvars; then
        T1=$(date +%s)
        echo "✓ Done in $((T1-T0))s"
    else
        echo "✗ FAILED: $name"
        fail=$((fail + 1))
    fi

    # Unset env vars for next experiment
    for kv in $envvars; do
        varname="${kv%%=*}"
        unset "$varname" 2>/dev/null || true
    done

    echo ""
done < "$QUEUE_FILE"

echo "===== Timed queue finished at $(date) ====="
echo "Completed: $count | Failed: $fail | Skipped: $skip"
