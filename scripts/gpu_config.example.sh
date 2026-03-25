#!/usr/bin/env bash
# Copy this file to scripts/gpu_config.sh and fill in real values.
# Keep scripts/gpu_config.sh local-only; it is gitignored on purpose.
#
# NOTE: REMOTE_DIR is NOT here — it's per-project, in projects/<name>.json
# under "gpu_remote_dirs". Use project_remote_dir() to resolve it.

# Example GPU entry
GPU_example_gpu_HOST="your-hostname"
GPU_example_gpu_PORT="22"
GPU_example_gpu_USER="root"
GPU_example_gpu_PASS="replace-me"

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

# Helper: resolve REMOTE_DIR for a project + GPU combo
# Usage: project_remote_dir <project_json_path> <gpu_name>
project_remote_dir() {
    local project_json="$1" gpu_name="$2"
    python3 -c "
import json, sys
p = json.load(open('$project_json'))
dirs = p.get('gpu_remote_dirs', {})
d = dirs.get('$gpu_name')
if not d:
    print(f'ERROR: No remote_dir for GPU $gpu_name in project config', file=sys.stderr)
    sys.exit(1)
print(d)
"
}

# Helper: resolve project config path from a project name
project_config_path() {
    local autoresearch_dir="$1" project_name="$2"
    echo "$autoresearch_dir/projects/$project_name.json"
}

# Helper: get a scalar or JSON value from project config by dotted path.
project_json_get() {
    local project_json="$1" field_path="$2" default="${3-__NO_DEFAULT__}"
    python3 -c "
import json, sys
path = '$field_path'.split('.')
obj = json.load(open('$project_json'))
for part in path:
    if isinstance(obj, dict):
        obj = obj.get(part)
    else:
        obj = None
        break
if obj is None:
    if '$default' != '__NO_DEFAULT__':
        print('$default')
    else:
        print(f'ERROR: Missing field $field_path in project config', file=sys.stderr)
        sys.exit(1)
elif isinstance(obj, bool):
    print('true' if obj else 'false')
elif isinstance(obj, (dict, list)):
    print(json.dumps(obj))
else:
    print(obj)
"
}

# Helper: check whether a project config exists
project_exists() {
    local autoresearch_dir="$1" project_name="$2"
    [ -f "$(project_config_path "$autoresearch_dir" "$project_name")" ]
}

# Helper: resolve the single enabled project for legacy one-project commands.
default_project_name() {
    local autoresearch_dir="$1"
    python3 -c "
from pathlib import Path
import json
import sys
files = sorted((Path('$autoresearch_dir') / 'projects').glob('*.json'))
enabled = []
for path in files:
    cfg = json.load(open(path))
    if cfg.get('enabled', True):
        enabled.append(path.stem)
if not enabled:
    print('ERROR: No enabled project configs found', file=sys.stderr)
    sys.exit(1)
if len(enabled) != 1:
    print(f'ERROR: Legacy shorthand is ambiguous with enabled projects: {enabled}. Pass <project> explicitly.', file=sys.stderr)
    sys.exit(1)
print(enabled[0])
"
}

# Helper: find which project owns a snapshot name.
snapshot_project_by_name() {
    local autoresearch_dir="$1" experiment_name="$2"
    python3 -c "
from pathlib import Path
import sys
root = Path('$autoresearch_dir') / 'experiments'
matches = []
for proj_dir in sorted(root.iterdir() if root.exists() else []):
    snap = proj_dir / 'snapshots' / '$experiment_name'
    if snap.is_dir():
        matches.append(proj_dir.name)
if not matches:
    print(f'ERROR: No snapshot named $experiment_name found under experiments/<project>/snapshots/', file=sys.stderr)
    sys.exit(1)
if len(matches) > 1:
    print(f'ERROR: Snapshot name $experiment_name exists in multiple projects: {matches}. Pass <project> explicitly.', file=sys.stderr)
    sys.exit(1)
print(matches[0])
"
}

# Helper: whether a project is enabled for auto-dispatch and legacy shorthand.
project_enabled() {
    local project_json="$1"
    [ "$(project_json_get "$project_json" enabled true)" != "false" ]
}

# Helper: resolve a per-project hook script path, if configured.
project_hook_path() {
    local project_json="$1" hook_name="$2" autoresearch_dir="$3"
    local hook
    hook="$(project_json_get "$project_json" "hooks.$hook_name" "" 2>/dev/null || true)"
    if [ -z "$hook" ]; then
        return 1
    fi
    case "$hook" in
        /*) printf '%s\n' "$hook" ;;
        *) printf '%s\n' "$autoresearch_dir/$hook" ;;
    esac
}

# Helper: read a field from project config JSON
project_field() {
    local project_json="$1" field="$2"
    if [ $# -ge 3 ]; then
        project_json_get "$project_json" "$field" "$3"
    else
        project_json_get "$project_json" "$field"
    fi
}

# Helper: resolve project name from an experiment's meta.json
experiment_project() {
    local snapshot_dir="$1"
    if [ -f "$snapshot_dir/meta.json" ]; then
        python3 -c "
import json
meta = json.load(open('$snapshot_dir/meta.json'))
print(meta.get('project', ''))
" | grep -v '^$' && return 0
    fi
    echo ""
}
