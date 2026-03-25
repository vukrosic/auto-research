#!/bin/bash
# Pull experiment results from all remote GPUs via SCP.
# Auto-detects GPUs from gpu_creds.sh.
# Usage:
#   infra/pull_results.sh              # pull all results from all GPUs
#   infra/pull_results.sh ARCH1 ARCH2  # pull only from specific GPUs

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_creds.sh"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o LogLevel=ERROR"
SCP_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o LogLevel=ERROR"

# Directories to pull from each GPU
REMOTE_DIRS=("/root/results" "/root/logs")
LOCAL_RESULTS="$REPO_DIR/results"

# Colors
if [[ -t 1 ]]; then
    GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'
    CYAN=$'\033[36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
    GREEN=""; YELLOW=""; RED=""; CYAN=""; BOLD=""; RESET=""
fi

# ---- Auto-detect GPUs ----
declare -a G_NAMES G_LABELS G_PORTS G_PASSES

while IFS='=' read -r key val; do
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ "$key" =~ ^GPU_(.+)_PORT$ ]] || continue
    gname="${BASH_REMATCH[1]}"
    port="${val//[\"\' ]/}"
    pvar="GPU_${gname}_PASS"
    pass="${!pvar//[\"\']/}"
    [[ -z "$port" || -z "$pass" ]] && continue
    case "$gname" in
        *3090*) label="REMOTE 3090" ;;
        *5090*) label="RTX 5090"    ;;
        *)      label="$gname"      ;;
    esac
    G_NAMES+=("$gname"); G_LABELS+=("$label"); G_PORTS+=("$port"); G_PASSES+=("$pass")
done < "$SCRIPT_DIR/gpu_creds.sh"

# Filter to requested GPUs if args provided
FILTER=("$@")

should_pull() {
    local name="$1"
    [[ "${#FILTER[@]}" -eq 0 ]] && return 0
    for f in "${FILTER[@]}"; do
        [[ "${name,,}" == "${f,,}" ]] && return 0
    done
    return 1
}

# ---- Pull from one GPU ----
pull_gpu() {
    local name="$1" label="$2" port="$3" pass="$4"
    local dest="$LOCAL_RESULTS" new=0 skip=0 failed=0

    printf "%b%-14s%b " "$BOLD$CYAN" "$label" "$RESET"

    # Get list of result dirs on remote
    remote_dirs=$(sshpass -p "$pass" ssh $SSH_OPTS -p "$port" root@"$HOST" \
        'ls -d /root/results/*/ 2>/dev/null | xargs -I{} basename {}' 2>/dev/null)

    if [[ -z "$remote_dirs" ]]; then
        printf "%bno results yet%b\n" "$YELLOW" "$RESET"
        return
    fi

    local count=0
    while IFS= read -r run_id; do
        [[ -z "$run_id" ]] && continue
        local local_path="$dest/$run_id"

        # Skip if already pulled (check summary.json exists)
        if [[ -f "$local_path/summary.json" ]]; then
            ((skip++))
            continue
        fi

        sshpass -p "$pass" scp $SCP_OPTS -r -P "$port" \
            "root@${HOST}:/root/results/${run_id}" \
            "$dest/" 2>/dev/null

        if [[ -f "$local_path/summary.json" ]]; then
            ((new++))
        else
            rmdir "$local_path" 2>/dev/null
            ((failed++))
        fi
        ((count++))
    done <<< "$remote_dirs"

    # Summary line
    local parts=()
    ((new    > 0)) && parts+=("${GREEN}+${new} new${RESET}")
    ((skip   > 0)) && parts+=("${YELLOW}${skip} already pulled${RESET}")
    ((failed > 0)) && parts+=("${RED}${failed} failed${RESET}")
    [[ ${#parts[@]} -eq 0 ]] && parts+=("${YELLOW}nothing pulled${RESET}")

    local msg
    msg=$(IFS=', '; printf '%b' "${parts[*]}")
    printf "%b\n" "$msg"
}

# ---- Main ----
mkdir -p "$LOCAL_RESULTS"
printf "\n%bPulling results → %s%b\n" "$BOLD" "$LOCAL_RESULTS" "$RESET"
printf '%0.s─' {1..60}; printf '\n'

PULLED=0
for i in "${!G_NAMES[@]}"; do
    name="${G_NAMES[$i]}"
    should_pull "$name" || continue
    pull_gpu "$name" "${G_LABELS[$i]}" "${G_PORTS[$i]}" "${G_PASSES[$i]}"
    ((PULLED++))
done

[[ $PULLED -eq 0 ]] && printf "%bNo matching GPUs found. Available: %s%b\n" \
    "$RED" "${G_NAMES[*]}" "$RESET"

printf '%0.s─' {1..60}; printf '\n'
printf "Done. Results in: %s\n\n" "$LOCAL_RESULTS"
