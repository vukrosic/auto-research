"""Fleet routes — GPU management with real SSH connectivity or local execution. Admin only."""
import re
import shlex
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import GPU, User
from api.routers.auth import get_current_user
from engine.sync import sync_creds_to_file

router = APIRouter()
LOCAL_GPU_HOSTS = {"localhost", "127.0.0.1", "local"}


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.tier != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


class GPUAdd(BaseModel):
    """Accept an SSH command string like: ssh -p 62132 root@proxy.us-ca-6.gpu-instance.novita.ai"""
    ssh_command: str
    name: str = ""
    password: str = ""
    hourly_rate: float = 0.0


class GPURunCommand(BaseModel):
    command: str


def parse_ssh_command(cmd: str) -> dict:
    """Parse 'ssh -p 62132 root@host.com' into components."""
    cmd = cmd.strip()
    # Remove leading 'ssh ' if present
    if cmd.lower().startswith("ssh "):
        cmd = cmd[4:].strip()

    port = 22
    # Extract -p port
    port_match = re.search(r'-p\s+(\d+)', cmd)
    if port_match:
        port = int(port_match.group(1))
        cmd = re.sub(r'-p\s+\d+', '', cmd).strip()

    # Find user@host — it's the token containing @
    parts = cmd.split()
    user_host = None
    for part in parts:
        if '@' in part:
            user_host = part
            break

    if user_host:
        user, host = user_host.split('@', 1)
    else:
        # No @, take the last non-flag token as host
        tokens = [p for p in parts if not p.startswith('-')]
        host = tokens[-1] if tokens else cmd
        user = 'root'

    return {"host": host.strip(), "port": port, "user": user.strip()}


def is_local_gpu(gpu: GPU) -> bool:
    return gpu.host in LOCAL_GPU_HOSTS


def ssh_exec(gpu: GPU, command: str, timeout: int = 15) -> tuple[int, str]:
    """Execute a command on a GPU via SSH or locally. Returns (returncode, output)."""
    if is_local_gpu(gpu):
        try:
            result = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=gpu.repo_path if Path(gpu.repo_path).exists() else None,
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return -1, "Local command timed out"

    ssh_cmd = [
        "sshpass", "-p", gpu.password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-p", str(gpu.port),
        f"{gpu.user}@{gpu.host}",
        command
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "Connection timed out"
    except FileNotFoundError:
        return -1, "sshpass not installed. Run: apt-get install -y sshpass"


def ensure_local_gpu(db: Session) -> GPU:
    """Ensure the local machine's main GPU exists as a fleet target."""
    existing = db.query(GPU).filter(GPU.host == "localhost", GPU.repo_path == "/root/parameter-golf").first()
    if existing:
        return existing

    gpu = GPU(
        name="local-3090",
        host="localhost",
        port=22,
        user="root",
        password="",
        repo_path="/root/parameter-golf",
        status="online",
    )
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return gpu


@router.post("/add")
def add_gpu(gpu_data: GPUAdd, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Add a GPU by pasting an SSH command + password.

    Tests connectivity, detects GPU type, checks if parameter-golf repo is set up.
    Example SSH command: ssh -p 62132 root@proxy.us-ca-6.gpu-instance.novita.ai
    """
    parsed = parse_ssh_command(gpu_data.ssh_command)

    # Auto-generate name from host if not provided
    name = gpu_data.name or parsed["host"].split(".")[0] + f"_{parsed['port']}"

    # Check if already exists
    existing = db.query(GPU).filter(GPU.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"GPU '{name}' already exists")

    gpu = GPU(
        name=name,
        host=parsed["host"],
        port=parsed["port"],
        user=parsed["user"],
        password=gpu_data.password,
        hourly_rate=gpu_data.hourly_rate,
        repo_path="/root/parameter-golf",
    )
    db.add(gpu)
    db.commit()
    db.refresh(gpu)

    # Test connection + detect GPU + check repo
    detect_cmd = (
        "echo '---HOSTNAME---' && hostname && "
        "echo '---GPU---' && nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo 'no-gpu' && "
        "echo '---REPO---' && (test -f /root/parameter-golf/train_gpt.py && echo 'ready' || echo 'not-setup') && "
        "echo '---DATA---' && (test -d /root/parameter-golf/data/datasets && echo 'ready' || echo 'not-downloaded')"
    )
    returncode, output = ssh_exec(gpu, detect_cmd, timeout=20)

    result = {"id": gpu.id, "name": gpu.name}

    if returncode != 0:
        gpu.status = "offline"
        db.commit()
        result["status"] = "offline"
        result["error"] = output.strip()
        return result

    gpu.status = "online"
    gpu.last_seen = datetime.now(timezone.utc)

    # Parse detection output
    sections = output.split("---")
    gpu_type = None
    repo_ready = False
    data_ready = False
    hostname = ""

    for i, section in enumerate(sections):
        header = section.strip().rstrip("---").strip()
        value = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if header == "HOSTNAME":
            hostname = value.split("\n")[0].strip()
        elif header == "GPU":
            gpu_type = value.split("\n")[0].strip() if value.strip() != "no-gpu" else None
        elif header == "REPO":
            repo_ready = "ready" in value
        elif header == "DATA":
            data_ready = "ready" in value

    db.commit()

    result["status"] = "online"
    result["hostname"] = hostname
    result["gpu_type"] = gpu_type
    result["repo_ready"] = repo_ready
    result["data_ready"] = data_ready

    warnings = []
    if not repo_ready:
        warnings.append("parameter-golf not found at /root/parameter-golf — run /setup on this GPU")
    if not data_ready:
        warnings.append("Training data not downloaded — run: python3 data/cached_challenge_fineweb.py --variant sp1024")
    if warnings:
        result["warnings"] = warnings

    # Sync gpu_creds.sh so parameter-golf CLI works standalone
    sync_creds_to_file(db)

    return result


@router.get("/")
def list_gpus(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """List all GPUs in the fleet."""
    ensure_local_gpu(db)
    gpus = db.query(GPU).order_by(GPU.added_at.desc()).all()
    return [
        {
            "id": g.id, "name": g.name, "host": g.host, "port": g.port,
            "status": g.status, "current_experiment": g.current_experiment,
            "current_step": g.current_step, "gpu_utilization": g.gpu_utilization,
            "gpu_temp": g.gpu_temp, "hourly_rate": g.hourly_rate,
            "last_seen": g.last_seen,
        }
        for g in gpus
    ]


@router.post("/{gpu_id}/test")
def test_gpu(gpu_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Test SSH connectivity to a GPU."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    returncode, output = ssh_exec(gpu, "echo OK && nvidia-smi --query-gpu=utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo 'no nvidia-smi'")

    if returncode == 0:
        gpu.status = "online"
        gpu.last_seen = datetime.now(timezone.utc)
        # Parse nvidia-smi output
        lines = output.strip().split("\n")
        if len(lines) >= 2 and "," in lines[1]:
            parts = lines[1].split(",")
            gpu.gpu_utilization = float(parts[0].strip())
            gpu.gpu_temp = float(parts[1].strip())
            gpu.status = "idle" if gpu.gpu_utilization < 50 else "training"
        db.commit()
        return {"status": "online", "output": output.strip()}
    else:
        gpu.status = "offline"
        db.commit()
        raise HTTPException(status_code=502, detail=f"SSH failed: {output.strip()}")


@router.post("/{gpu_id}/exec")
def exec_on_gpu(gpu_id: int, cmd: GPURunCommand, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Execute an arbitrary command on a GPU (admin only)."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    returncode, output = ssh_exec(gpu, cmd.command, timeout=30)
    return {"returncode": returncode, "output": output}


@router.post("/{gpu_id}/run-experiment")
def run_experiment_on_gpu(gpu_id: int, experiment_name: str, steps: int, overrides: str = "", db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Run an experiment on a specific GPU."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    # Validate overrides: only allow KEY=VALUE pairs with safe characters
    if overrides:
        if not all(re.match(r'^[A-Z_][A-Z0-9_]*=[A-Za-z0-9._-]+$', part) for part in overrides.split()):
            raise HTTPException(status_code=400, detail="Invalid overrides format. Use KEY=VALUE pairs only.")

    # Build command with shell-safe quoting
    safe_name = shlex.quote(experiment_name)
    cmd = f"cd {gpu.repo_path} && {overrides} bash infra/run_experiment.sh {safe_name} {steps}".strip()

    # Run in background on GPU via nohup
    bg_cmd = f"nohup bash -c '{cmd}' > /tmp/{safe_name}.log 2>&1 &"
    returncode, output = ssh_exec(gpu, bg_cmd, timeout=15)

    if returncode == 0:
        gpu.status = "training"
        gpu.current_experiment = experiment_name
        gpu.current_step = 0
        db.commit()
        return {"status": "started", "experiment": experiment_name, "gpu": gpu.name}
    else:
        return {"status": "failed", "error": output}


@router.post("/{gpu_id}/status")
def check_gpu_status(gpu_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Check detailed training status on a GPU."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    # Check if training is running and get latest log output
    cmd = """
    nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null;
    echo '---';
    ls -t /tmp/*.log 2>/dev/null | head -1 | xargs tail -5 2>/dev/null || echo 'no logs';
    echo '---';
    pgrep -f train_gpt | head -1 || echo 'no training process'
    """
    returncode, output = ssh_exec(gpu, cmd, timeout=15)

    if returncode != 0:
        gpu.status = "offline"
        db.commit()
        return {"status": "offline", "error": output}

    parts = output.split("---")
    gpu_info = parts[0].strip() if len(parts) > 0 else ""
    log_tail = parts[1].strip() if len(parts) > 1 else ""
    process = parts[2].strip() if len(parts) > 2 else ""

    is_training = process and process != "no training process"
    gpu.status = "training" if is_training else "idle"
    gpu.last_seen = datetime.now(timezone.utc)

    if gpu_info and "," in gpu_info:
        vals = gpu_info.split(",")
        gpu.gpu_utilization = float(vals[0].strip())
        gpu.gpu_temp = float(vals[1].strip())

    db.commit()

    return {
        "status": gpu.status,
        "gpu_info": gpu_info,
        "log_tail": log_tail,
        "is_training": is_training,
        "current_experiment": gpu.current_experiment,
    }


@router.delete("/{gpu_id}")
def remove_gpu(gpu_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Remove a GPU from the fleet."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if is_local_gpu(gpu):
        raise HTTPException(status_code=400, detail="Local GPU cannot be removed")
    name = gpu.name
    db.delete(gpu)
    db.commit()
    # Re-sync gpu_creds.sh after removal
    sync_creds_to_file(db)
    return {"deleted": name}
