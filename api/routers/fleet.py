"""Fleet routes — GPU management with real SSH connectivity."""
import re
import subprocess
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import GPU

router = APIRouter()


class GPUAdd(BaseModel):
    """Accept an SSH command string like: ssh -p 62132 root@proxy.us-ca-6.gpu-instance.novita.ai"""
    ssh_command: str
    name: str = ""
    password: str = ""


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


def ssh_exec(gpu: GPU, command: str, timeout: int = 15) -> tuple[int, str]:
    """Execute a command on a GPU via SSH. Returns (returncode, output)."""
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


@router.post("/add")
def add_gpu(gpu_data: GPUAdd, db: Session = Depends(get_db)):
    """Add a GPU by pasting an SSH command.

    Example input: ssh -p 62132 root@proxy.us-ca-6.gpu-instance.novita.ai
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
        repo_path="/root/parameter-golf",
    )
    db.add(gpu)
    db.commit()
    db.refresh(gpu)

    # Test connection
    returncode, output = ssh_exec(gpu, "echo 'connected' && hostname")
    if returncode == 0:
        gpu.status = "online"
        gpu.last_seen = datetime.now(timezone.utc)
        db.commit()
        return {"id": gpu.id, "name": gpu.name, "status": "online", "output": output.strip()}
    else:
        gpu.status = "offline"
        db.commit()
        return {"id": gpu.id, "name": gpu.name, "status": "offline", "error": output.strip()}


@router.get("/")
def list_gpus(db: Session = Depends(get_db)):
    """List all GPUs in the fleet."""
    gpus = db.query(GPU).order_by(GPU.added_at.desc()).all()
    return [
        {
            "id": g.id, "name": g.name, "host": g.host, "port": g.port,
            "status": g.status, "current_experiment": g.current_experiment,
            "current_step": g.current_step, "gpu_utilization": g.gpu_utilization,
            "gpu_temp": g.gpu_temp, "last_seen": g.last_seen,
        }
        for g in gpus
    ]


@router.post("/{gpu_id}/test")
def test_gpu(gpu_id: int, db: Session = Depends(get_db)):
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
def exec_on_gpu(gpu_id: int, cmd: GPURunCommand, db: Session = Depends(get_db)):
    """Execute an arbitrary command on a GPU (admin only)."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    returncode, output = ssh_exec(gpu, cmd.command, timeout=30)
    return {"returncode": returncode, "output": output}


@router.post("/{gpu_id}/run-experiment")
def run_experiment_on_gpu(gpu_id: int, experiment_name: str, steps: int, overrides: str = "", db: Session = Depends(get_db)):
    """Run an experiment on a specific GPU."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    # Build command
    cmd = f"cd {gpu.repo_path} && {overrides} bash infra/run_experiment.sh {experiment_name} {steps}".strip()

    # Run in background on GPU via nohup
    bg_cmd = f"nohup bash -c '{cmd}' > /tmp/{experiment_name}.log 2>&1 &"
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
def check_gpu_status(gpu_id: int, db: Session = Depends(get_db)):
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
def remove_gpu(gpu_id: int, db: Session = Depends(get_db)):
    """Remove a GPU from the fleet."""
    gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    db.delete(gpu)
    db.commit()
    return {"deleted": gpu.name}
