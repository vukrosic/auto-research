#!/usr/bin/env python3
"""Export commit-friendly experiment artifacts from a training log."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

STEP_VAL_RE = re.compile(
    r"step:(?P<step>\d+)/(?P<max_steps>\d+)\s+val_loss:(?P<val_loss>[0-9.]+)\s+val_bpb:(?P<val_bpb>[0-9.]+)"
)
FINAL_QUANT_RE = re.compile(
    r"final_int8_zlib_roundtrip_exact\s+val_loss:(?P<val_loss>[0-9.]+)\s+val_bpb:(?P<val_bpb>[0-9.]+)"
)
INT8_BYTES_RE = re.compile(r"Serialized model int8\+zlib:\s+(?P<bytes>\d+)\s+bytes")
TOTAL_BYTES_RE = re.compile(r"Total submission size int8\+zlib:\s+(?P<bytes>\d+)\s+bytes")


def run_cmd(cmd: list[str]) -> str | None:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return out or None


def parse_log(log_path: Path) -> dict:
    metrics: dict[str, object] = {
        "last_eval": None,
        "final_quant_eval": None,
        "int8_zlib_model_bytes": None,
        "int8_zlib_total_submission_bytes": None,
    }
    if not log_path.exists():
        return metrics

    last_eval = None
    final_quant_eval = None
    int8_model_bytes = None
    int8_total_bytes = None

    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            step_match = STEP_VAL_RE.search(line)
            if step_match:
                last_eval = {
                    "step": int(step_match.group("step")),
                    "max_steps": int(step_match.group("max_steps")),
                    "val_loss": float(step_match.group("val_loss")),
                    "val_bpb": float(step_match.group("val_bpb")),
                }
            final_quant_match = FINAL_QUANT_RE.search(line)
            if final_quant_match:
                final_quant_eval = {
                    "val_loss": float(final_quant_match.group("val_loss")),
                    "val_bpb": float(final_quant_match.group("val_bpb")),
                }
            int8_match = INT8_BYTES_RE.search(line)
            if int8_match:
                int8_model_bytes = int(int8_match.group("bytes"))
            total_match = TOTAL_BYTES_RE.search(line)
            if total_match:
                int8_total_bytes = int(total_match.group("bytes"))

    metrics["last_eval"] = last_eval
    metrics["final_quant_eval"] = final_quant_eval
    metrics["int8_zlib_model_bytes"] = int8_model_bytes
    metrics["int8_zlib_total_submission_bytes"] = int8_total_bytes
    return metrics


def get_git_metadata() -> dict[str, object]:
    commit = run_cmd(["git", "rev-parse", "HEAD"])
    short = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    dirty = run_cmd(["git", "status", "--porcelain"])
    return {
        "commit": commit,
        "commit_short": short,
        "dirty_worktree": bool(dirty),
    }


def get_gpu_metadata() -> dict[str, object]:
    query = run_cmd(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ]
    )
    if not query:
        return {"detected": False}
    first = query.splitlines()[0]
    parts = [p.strip() for p in first.split(",")]
    return {
        "detected": True,
        "name": parts[0] if len(parts) > 0 else None,
        "memory_total": parts[1] if len(parts) > 1 else None,
        "driver_version": parts[2] if len(parts) > 2 else None,
    }


def collect_config() -> dict[str, object]:
    keys = [
        "RUN_ID",
        "ITERATIONS",
        "MAX_WALLCLOCK_SECONDS",
        "VAL_LOSS_EVERY",
        "TRAIN_LOG_EVERY",
        "SEED",
        "MATRIX_LR",
        "SCALAR_LR",
        "EMBED_LR",
        "NUM_LAYERS",
        "MODEL_DIM",
        "NUM_HEADS",
        "NUM_KV_HEADS",
        "MLP_MULT",
        "WARMDOWN_ITERS",
        "WARMUP_STEPS",
        "LOGIT_SOFTCAP",
        "QK_GAIN_INIT",
        "ROPE_BASE",
        "MUON_MOMENTUM",
        "MUON_BACKEND_STEPS",
        "GRAD_CLIP_NORM",
        "TIED_EMBED_LR",
        "TIED_EMBED_INIT_STD",
        "TOKENIZER_PATH",
        "VOCAB_SIZE",
        "DATA_PATH",
    ]
    return {k: os.environ[k] for k in keys if k in os.environ}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log_path)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics = parse_log(log_path)

    summary = {
        "run_id": args.run_id,
        "generated_at_utc": now,
        "last_eval": metrics["last_eval"],
        "final_quant_eval": metrics["final_quant_eval"],
        "int8_zlib_model_bytes": metrics["int8_zlib_model_bytes"],
        "int8_zlib_total_submission_bytes": metrics["int8_zlib_total_submission_bytes"],
    }

    metadata = {
        "run_id": args.run_id,
        "generated_at_utc": now,
        "log_path": str(log_path),
        "git": get_git_metadata(),
        "hardware": {"gpu": get_gpu_metadata()},
        "config": collect_config(),
    }

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "metadata.json", metadata)


if __name__ == "__main__":
    main()
