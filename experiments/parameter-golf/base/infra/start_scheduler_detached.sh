#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs

if pgrep -f "python3 infra/gpu_scheduler.py" >/dev/null 2>&1; then
  echo "scheduler already running"
  pgrep -af "python3 infra/gpu_scheduler.py"
  exit 0
fi

nohup python3 infra/gpu_scheduler.py >> logs/gpu_scheduler.log 2>&1 < /dev/null &
echo $! > logs/gpu_scheduler.pid
echo "started scheduler pid $(cat logs/gpu_scheduler.pid)"
