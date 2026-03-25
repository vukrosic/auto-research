#!/usr/bin/env python3
"""
Analyze and compare experiment results from parameter-golf logs.

Usage:
    python3 infra/analyze.py                          # Show all experiments
    python3 infra/analyze.py logs/exp1.txt logs/exp2.txt  # Compare specific logs
    python3 infra/analyze.py --step 500               # Compare val_bpb at step 500
    python3 infra/analyze.py --plot                    # Plot loss curves (requires matplotlib)
"""

import argparse
import glob
import os
import re
import sys
from pathlib import Path


def parse_log(filepath: str) -> dict:
    """Parse a training log file into structured data."""
    result = {
        "path": filepath,
        "name": Path(filepath).stem,
        "config": {},
        "train_steps": [],
        "val_steps": [],
        "final_quant_bpb": None,
        "final_quant_loss": None,
    }

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()

            # Parse config lines
            config_patterns = {
                "matrix_lr": r"matrix_lr:([\d.]+)",
                "scalar_lr": r"scalar_lr:([\d.]+)",
                "embed_lr": r"embed_lr:([\d.]+)",
                "model_params": r"model_params:(\d+)",
                "world_size": r"world_size:(\d+)",
                "grad_accum": r"grad_accum_steps:(\d+)",
                "num_heads": r"num_heads:(\d+)",
                "num_kv_heads": r"num_kv_heads:(\d+)",
                "train_batch_tokens": r"train_batch_tokens:(\d+)",
                "warmdown_iters": r"warmdown_iters:(\d+)",
            }
            for key, pattern in config_patterns.items():
                m = re.search(pattern, line)
                if m:
                    result["config"][key] = m.group(1)

            # Parse training steps
            m = re.match(
                r"step:(\d+)/\d+ train_loss:([\d.]+) train_time:(\d+)ms step_avg:([\d.]+)ms",
                line,
            )
            if m:
                result["train_steps"].append({
                    "step": int(m.group(1)),
                    "train_loss": float(m.group(2)),
                    "train_time_ms": int(m.group(3)),
                    "step_avg_ms": float(m.group(4)),
                })

            # Parse validation steps
            m = re.match(
                r"step:(\d+)/\d+ val_loss:([\d.]+) val_bpb:([\d.]+)",
                line,
            )
            if m:
                result["val_steps"].append({
                    "step": int(m.group(1)),
                    "val_loss": float(m.group(2)),
                    "val_bpb": float(m.group(3)),
                })

            # Parse final quant roundtrip
            m = re.match(
                r"final_int8_zlib_roundtrip_exact val_loss:([\d.]+) val_bpb:([\d.]+)",
                line,
            )
            if m:
                result["final_quant_loss"] = float(m.group(1))
                result["final_quant_bpb"] = float(m.group(2))

    return result


def get_bpb_at_step(result: dict, target_step: int) -> float | None:
    """Get val_bpb at or nearest to target_step."""
    if not result["val_steps"]:
        return None
    closest = min(result["val_steps"], key=lambda v: abs(v["step"] - target_step))
    return closest["val_bpb"]


def get_last_bpb(result: dict) -> float | None:
    """Get the last recorded val_bpb."""
    if not result["val_steps"]:
        return None
    return result["val_steps"][-1]["val_bpb"]


def get_last_step(result: dict) -> int:
    """Get the last recorded step."""
    all_steps = [s["step"] for s in result["train_steps"]] + [
        s["step"] for s in result["val_steps"]
    ]
    return max(all_steps) if all_steps else 0


def format_table(results: list[dict], target_step: int | None = None) -> str:
    """Format results as a comparison table."""
    lines = []

    header = f"{'Name':<35} {'Steps':>7} {'Last BPB':>10} {'Quant BPB':>11} {'LR(mat)':>8} {'Params':>10}"
    if target_step:
        header += f" {'BPB@{target_step}':>12}"
    lines.append(header)
    lines.append("-" * len(header))

    # Sort by last BPB (lower is better)
    sorted_results = sorted(results, key=lambda r: get_last_bpb(r) or 99.0)

    for r in sorted_results:
        last_bpb = get_last_bpb(r)
        quant_bpb = r["final_quant_bpb"]
        mat_lr = r["config"].get("matrix_lr", "?")
        params = r["config"].get("model_params", "?")
        steps = get_last_step(r)

        row = (
            f"{r['name']:<35} "
            f"{steps:>7} "
            f"{last_bpb:>10.4f} " if last_bpb else f"{'N/A':>10} "
        )
        row += f"{quant_bpb:>11.4f} " if quant_bpb else f"{'N/A':>11} "
        row += f"{mat_lr:>8} {params:>10}"

        if target_step:
            step_bpb = get_bpb_at_step(r, target_step)
            row += f" {step_bpb:>12.4f}" if step_bpb else f" {'N/A':>12}"

        lines.append(row)

    # Add baseline reference
    lines.append("-" * len(header))
    ref = f"{'[BASELINE RECORD]':<35} {'13780':>7} {'1.2172':>10} {'1.2244':>11} {'0.04':>8} {'17059912':>10}"
    lines.append(ref)

    return "\n".join(lines)


def plot_curves(results: list[dict], metric: str = "val_bpb") -> None:
    """Plot training curves (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    for r in results:
        if metric == "val_bpb" and r["val_steps"]:
            steps = [v["step"] for v in r["val_steps"]]
            values = [v["val_bpb"] for v in r["val_steps"]]
            ax.plot(steps, values, label=r["name"], marker=".", markersize=3)
        elif metric == "train_loss" and r["train_steps"]:
            steps = [t["step"] for t in r["train_steps"]]
            values = [t["train_loss"] for t in r["train_steps"]]
            ax.plot(steps, values, label=r["name"], alpha=0.7)

    ax.set_xlabel("Step")
    ax.set_ylabel(metric)
    ax.set_title(f"Parameter Golf: {metric} comparison")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Add baseline reference line
    if metric == "val_bpb":
        ax.axhline(y=1.2244, color="red", linestyle="--", alpha=0.5, label="Baseline (1.2244)")

    plt.tight_layout()
    plt.savefig("research/figures/comparison.png", dpi=150)
    print("Saved plot to research/figures/comparison.png")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Analyze parameter-golf experiments")
    parser.add_argument("logs", nargs="*", help="Log files to compare")
    parser.add_argument("--step", type=int, help="Compare BPB at specific step")
    parser.add_argument("--plot", action="store_true", help="Plot loss curves")
    parser.add_argument(
        "--metric",
        default="val_bpb",
        choices=["val_bpb", "train_loss"],
        help="Metric to plot",
    )
    parser.add_argument("--dir", default="logs", help="Directory to scan for logs")
    args = parser.parse_args()

    # Find log files
    if args.logs:
        log_files = args.logs
    else:
        log_files = sorted(glob.glob(os.path.join(args.dir, "*.txt")))

    if not log_files:
        print(f"No log files found in {args.dir}/")
        sys.exit(1)

    # Parse all logs
    results = []
    for f in log_files:
        try:
            r = parse_log(f)
            if r["train_steps"] or r["val_steps"]:
                results.append(r)
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}", file=sys.stderr)

    if not results:
        print("No valid results found.")
        sys.exit(1)

    # Display table
    print(f"\n{'='*80}")
    print(f"  Parameter Golf Lab — {len(results)} experiments")
    print(f"{'='*80}\n")
    print(format_table(results, target_step=args.step))
    print()

    # Show quant gap for experiments that have it
    quant_results = [r for r in results if r["final_quant_bpb"] is not None]
    if quant_results:
        print("Quantization gaps:")
        for r in quant_results:
            last_bpb = get_last_bpb(r)
            if last_bpb:
                gap = r["final_quant_bpb"] - last_bpb
                print(f"  {r['name']}: {last_bpb:.4f} -> {r['final_quant_bpb']:.4f} (gap: {gap:+.4f})")
        print()

    if args.plot:
        plot_curves(results, metric=args.metric)


if __name__ == "__main__":
    main()
