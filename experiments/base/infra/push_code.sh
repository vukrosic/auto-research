#!/usr/bin/env bash
# Push local code files to a remote GPU via tar+ssh (no git needed).
#
# Usage:
#   infra/push_code.sh <GPU_NAME>                    # push default files
#   infra/push_code.sh <GPU_NAME> --files f1 f2 ...  # push specific files only
#   infra/push_code.sh <GPU_NAME> --all              # push full repo (excl. data/logs/results)
#
# Safe to run while experiments are training — processes already loaded the script at startup.
# New experiments launched after this push will use the updated code.
#
# What gets pushed by default:
#   train_gpt.py, infra/*.sh, requirements.txt, utils/
#
# Remote repo path is auto-detected (handles /root/parameter-golf or ~/parameter-golf).

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLEET_SCRIPTS="$REPO_ROOT/.claude/skills/fleet/scripts"

GPU_NAME="${1:?Usage: infra/push_code.sh <GPU_NAME> [--files f1 f2...] [--all]}"
shift

# Discover GPU credentials
GPU_INFO=$("$FLEET_SCRIPTS/discover_gpus.sh" | grep -i "^${GPU_NAME} " || true)
if [ -z "$GPU_INFO" ]; then
    echo "ERROR: GPU '$GPU_NAME' not found. Available:"
    "$FLEET_SCRIPTS/discover_gpus.sh" | awk '{print "  " $1}'
    exit 1
fi
PORT=$(echo "$GPU_INFO" | awk '{print $2}')
PASS=$(echo "$GPU_INFO" | awk '{print $3}')

source "$REPO_ROOT/infra/gpu_creds.sh"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -o LogLevel=ERROR"
export SSHPASS="$PASS"

# Auto-detect remote repo path
REMOTE_REPO=$(sshpass -e ssh $SSH_OPTS -p "$PORT" root@"$HOST" \
    'if [ -d /root/parameter-golf ]; then echo /root/parameter-golf; elif [ -d ~/parameter-golf ]; then echo ~/parameter-golf; else echo .; fi' 2>/dev/null)
echo "Remote repo: $REMOTE_REPO"

# Determine what to push
MODE="default"
FILES=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)   MODE="all"; shift ;;
        --files) MODE="files"; shift; while [[ $# -gt 0 && "$1" != --* ]]; do FILES+=("$1"); shift; done ;;
        *)       echo "Unknown arg: $1"; exit 1 ;;
    esac
done

cd "$REPO_ROOT"

case "$MODE" in
    default)
        echo "Pushing: train_gpt.py, infra/, utils/, requirements.txt → $GPU_NAME"
        tar czf - \
            train_gpt.py \
            requirements.txt \
            infra/*.sh \
            infra/*.py \
            utils/ \
            2>/dev/null \
        | sshpass -e ssh $SSH_OPTS -p "$PORT" root@"$HOST" \
            "tar xzf - -C '$REMOTE_REPO'"
        ;;
    files)
        echo "Pushing: ${FILES[*]} → $GPU_NAME"
        tar czf - "${FILES[@]}" 2>/dev/null \
        | sshpass -e ssh $SSH_OPTS -p "$PORT" root@"$HOST" \
            "tar xzf - -C '$REMOTE_REPO'"
        ;;
    all)
        echo "Pushing full repo (excl. data/, logs/, results/, checkpoints/) → $GPU_NAME"
        tar czf - \
            --exclude='./data/datasets' \
            --exclude='./logs' \
            --exclude='./results' \
            --exclude='./checkpoints' \
            --exclude='./.git' \
            . \
            2>/dev/null \
        | sshpass -e ssh $SSH_OPTS -p "$PORT" root@"$HOST" \
            "tar xzf - -C '$REMOTE_REPO'"
        ;;
esac

echo "Done — $GPU_NAME code updated."
