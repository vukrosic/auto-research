"""Multi-tenant GPU orchestrator.

Wraps parameter-golf's infra/ scripts to support multiple users
with tier-based priority scheduling.
"""
import subprocess
from pathlib import Path

from engine.templates import get_template


def build_experiment_command(
    template_name: str,
    experiment_name: str,
    steps: int,
    overrides: dict,
) -> str:
    """Build the shell command to run an experiment."""
    template = get_template(template_name)
    repo_path = Path(template.path)
    runner = repo_path / template.runner_script

    env_parts = " ".join(f"{k}={v}" for k, v in overrides.items())
    cmd = f"{env_parts} bash {runner} {experiment_name} {steps}".strip()
    return cmd


def submit_to_gpu(
    gpu_name: str,
    command: str,
    ssh_host: str,
    ssh_port: int,
    ssh_pass: str,
) -> dict:
    """Submit an experiment to a specific GPU via SSH.

    Uses the same SSH pattern as parameter-golf's infra scripts.
    """
    # TODO: Use sshpass or paramiko for password-based SSH
    # For now, return the command that would be run
    return {
        "gpu": gpu_name,
        "command": command,
        "status": "submitted",
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
