#!/usr/bin/env bash
# Copy this file to scripts/gpu_config.sh and fill in real values.
# Keep scripts/gpu_config.sh local-only; it is gitignored on purpose.

# Example GPU entry
GPU_example_gpu_HOST="your-hostname"
GPU_example_gpu_PORT="22"
GPU_example_gpu_USER="root"
GPU_example_gpu_PASS="replace-me"
GPU_example_gpu_REMOTE_DIR="/root/parameter-golf"

# List all configured GPU names, space-separated
ALL_GPUS="example-gpu"

# Helper: get GPU variable
gpu_var() {
    local gpu_name="$1" var_name="$2"
    local safe_name="${gpu_name//-/_}"
    local full_var="GPU_${safe_name}_${var_name}"
    echo "${!full_var}"
}

# Helper: SSH to a GPU
gpu_ssh() {
    local gpu="$1"; shift
    local host=$(gpu_var "$gpu" HOST)
    local port=$(gpu_var "$gpu" PORT)
    local user=$(gpu_var "$gpu" USER)
    local pass=$(gpu_var "$gpu" PASS)
    sshpass -p "$pass" ssh -p "$port" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${user}@${host}" "$@"
}

# Helper: rsync TO a GPU
gpu_rsync_to() {
    local gpu="$1" src="$2" dst="$3"
    local host=$(gpu_var "$gpu" HOST)
    local port=$(gpu_var "$gpu" PORT)
    local user=$(gpu_var "$gpu" USER)
    local pass=$(gpu_var "$gpu" PASS)
    sshpass -p "$pass" rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
        -e "ssh -p $port -o StrictHostKeyChecking=no" \
        "$src" "${user}@${host}:${dst}"
}

# Helper: rsync FROM a GPU
gpu_rsync_from() {
    local gpu="$1" src="$2" dst="$3"
    local host=$(gpu_var "$gpu" HOST)
    local port=$(gpu_var "$gpu" PORT)
    local user=$(gpu_var "$gpu" USER)
    local pass=$(gpu_var "$gpu" PASS)
    sshpass -p "$pass" rsync -avz \
        -e "ssh -p $port -o StrictHostKeyChecking=no" \
        "${user}@${host}:${src}" "$dst"
}
