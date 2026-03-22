"""Multi-tenant GPU orchestrator.

Wraps parameter-golf's infra/ scripts to support multiple users
with tier-based priority scheduling.
"""
import json
import shlex
from pathlib import Path

from api.models import GPU
from api.routers.fleet import ssh_exec
from engine.templates import get_template


def build_experiment_command(
    template_name: str,
    experiment_name: str,
    steps: int,
    overrides: dict,
    repo_path: str = "/root/parameter-golf",
) -> str:
    """Build the shell command to run an experiment on a remote GPU."""
    template = get_template(template_name)
    runner = f"{repo_path}/{template.runner_script}"

    # Filter to only allowed overrides
    valid = set(template.allowed_overrides)
    env_parts = " ".join(f"{k}={v}" for k, v in overrides.items() if k in valid)
    safe_name = shlex.quote(experiment_name)
    cmd = f"cd {repo_path} && {env_parts} bash {runner} {safe_name} {steps}".strip()
    return cmd


def submit_to_gpu(gpu: GPU, command: str) -> dict:
    """Submit an experiment to a specific GPU via SSH."""
    bg_cmd = f"nohup bash -c '{command}' > /tmp/experiment.log 2>&1 &"
    returncode, output = ssh_exec(gpu, bg_cmd, timeout=15)
    return {
        "gpu": gpu.name,
        "command": command,
        "status": "submitted" if returncode == 0 else "failed",
        "output": output,
    }


def get_queue_priority(tier: str) -> int:
    """Higher number = higher priority in the queue."""
    priorities = {
        "starter": 1,
        "researcher": 2,
        "pro": 3,
        "team": 3,
        "admin": 10,
    }
    return priorities.get(tier, 0)
