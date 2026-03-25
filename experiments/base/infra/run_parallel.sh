#!/usr/bin/env bash
# Worker-pool GPU scheduler: each GPU grabs the next job as soon as it finishes.
# No GPU ever sits idle while work remains in the queue.
set -uo pipefail
cd "$(dirname "$0")/.."

QUEUE_FILE="${1:-queues/active.txt}"
NUM_GPUS="${2:-8}"
FAIL_LOG="logs/failed_experiments.log"
LOCK_FILE="/tmp/gpu_scheduler.lock"

echo "===== Worker-pool scheduler started at $(date) ====="
echo "GPUs: $NUM_GPUS"
echo "Queue: $QUEUE_FILE"

# Collect all pending experiments into a shared job file
JOB_FILE=$(mktemp /tmp/gpu_jobs.XXXXXX)
while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// /}" ]] && continue

    name=$(echo "$line" | awk '{print $1}')

    # Skip if already done
    if [ -d "results/$name" ] && { [ -f "results/$name/train.log" ] || [ -f "results/$name/summary.json" ]; }; then
        echo "SKIP (done): $name"
        continue
    fi

    echo "$line" >> "$JOB_FILE"
done < "$QUEUE_FILE"

TOTAL=$(wc -l < "$JOB_FILE")
echo "Pending experiments: $TOTAL"
echo ""

mkdir -p logs 2>/dev/null

# Atomic job counter file
COUNTER_FILE=$(mktemp /tmp/gpu_counter.XXXXXX)
echo "0" > "$COUNTER_FILE"

# grab_next_job: atomically reads and increments the counter using flock.
# Returns the job index (0-based) or -1 if no more jobs.
grab_next_job() {
    (
        flock -x 200
        local idx
        idx=$(cat "$COUNTER_FILE")
        if [ "$idx" -ge "$TOTAL" ]; then
            echo "-1"
        else
            echo $((idx + 1)) > "$COUNTER_FILE"
            echo "$idx"
        fi
    ) 200>"$LOCK_FILE"
}

# Worker function: runs on one GPU, keeps grabbing jobs until none remain
gpu_worker() {
    local gpu_id=$1

    while true; do
        local job_idx
        job_idx=$(grab_next_job)

        # No more jobs
        if [ "$job_idx" = "-1" ]; then
            echo "[GPU $gpu_id] No more jobs. Worker exiting."
            break
        fi

        # Get the job line (1-indexed for sed)
        local line
        line=$(sed -n "$((job_idx + 1))p" "$JOB_FILE")

        local name=$(echo "$line" | awk '{print $1}')
        local steps=$(echo "$line" | awk '{print $2}')
        local envvars=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i}')

        echo "[GPU $gpu_id] Starting job $((job_idx + 1))/$TOTAL: $name ($steps steps) [$envvars]"

        local env_cmd="export CUDA_VISIBLE_DEVICES=$gpu_id;"
        for ev in $envvars; do
            [[ "$ev" =~ ^# ]] && break
            env_cmd="$env_cmd export $ev;"
        done

        local start_time=$(date +%s)
        (
            eval "$env_cmd"
            bash infra/run_experiment.sh "$name" "$steps"
        ) > "logs/${name}_gpu${gpu_id}.txt" 2>&1
        local exit_code=$?
        local end_time=$(date +%s)
        local elapsed=$(( end_time - start_time ))

        if [ $exit_code -ne 0 ]; then
            echo "[GPU $gpu_id] FAILED: $name (exit=$exit_code, ${elapsed}s)"
            echo "$(date) | $name | exit=$exit_code | ${elapsed}s | GPU=$gpu_id | $envvars" >> "$FAIL_LOG"
        else
            echo "[GPU $gpu_id] DONE: $name (${elapsed}s) [job $((job_idx + 1))/$TOTAL]"
        fi
    done
}

# Launch one worker per GPU
pids=()
for (( gpu=0; gpu<NUM_GPUS; gpu++ )); do
    gpu_worker $gpu &
    pids+=($!)
done

echo "Launched $NUM_GPUS workers. Waiting for all to finish..."

# Wait for all workers
for pid in "${pids[@]}"; do
    wait $pid
done

# Cleanup
rm -f "$JOB_FILE" "$COUNTER_FILE" "$LOCK_FILE"

echo ""
echo "===== Worker-pool scheduler finished at $(date) ====="
echo "Total experiments: $TOTAL"
