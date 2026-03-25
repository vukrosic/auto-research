#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"

INTERVAL="${1:-300}"

exec python3 "$SCRIPT_DIR/autonomous_lab.py" loop --interval "$INTERVAL" >> "$LOG_DIR/autonomous_lab.log" 2>&1
