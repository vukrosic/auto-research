#!/usr/bin/env python3
"""Append a completed experiment's timing to the central timing log."""
import json
import sys
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent
TIMING_LOG = AUTORESEARCH_DIR / "state" / "timing_log.md"

def main():
    if len(sys.argv) < 3:
        print("Usage: update_timing_log.py <name> <result.json> [meta.json]")
        sys.exit(1)

    name = sys.argv[1]
    result_path = Path(sys.argv[2])
    meta_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    meta = json.loads(meta_path.read_text()) if meta_path and meta_path.exists() else {}

    stage = meta.get("stage", "?")
    steps = meta.get("steps", result.get("steps_completed", "?"))
    gpu = result.get("gpu", meta.get("gpu", "?"))
    expected = result.get("expected_duration_seconds") or meta.get("expected_duration_seconds")
    actual = result.get("duration_seconds")
    dispatched_at = result.get("dispatched_at", "?")
    collected_at = result.get("collected_at", "?")
    val_bpb = result.get("val_bpb", "?")

    # Compute ratio and error
    if expected and actual:
        ratio = actual / expected
        error_pct = round((actual - expected) / expected * 100, 1)
        ratio_str = f"{ratio:.2f}x"
        error_str = f"{error_pct:+.1f}%"
    else:
        ratio_str = "?"
        error_str = "?"

    def fmt_sec(s):
        if s is None:
            return "?"
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h:
            return f"{h}h{m:02d}m{sec:02d}s"
        elif m:
            return f"{m}m{sec:02d}s"
        return f"{sec}s"

    row = (
        f"| {name} | {stage} | {steps} | {gpu} | "
        f"{fmt_sec(expected)} | {fmt_sec(actual)} | {ratio_str} | {error_str} | "
        f"{val_bpb} | {dispatched_at[:16] if dispatched_at != '?' else '?'} |"
    )

    # Initialize log if missing
    if not TIMING_LOG.exists():
        TIMING_LOG.write_text(
            "# Timing Log\n\n"
            "Tracks actual vs predicted experiment duration. Use this to improve future estimates.\n\n"
            "## Reference (RTX 3090)\n"
            "- Explore (500 steps): predicted 1680s (28 min)\n"
            "- Validate (4000 steps): predicted 13320s (3.7 hr)\n"
            "- Full (13780 steps): predicted 45720s (12.7 hr)\n"
            "- Per-step: ~644ms/step (measured)\n\n"
            "## Log\n\n"
            "| Experiment | Stage | Steps | GPU | Predicted | Actual | Ratio | Error% | val_bpb | Dispatched |\n"
            "|-----------|-------|-------|-----|-----------|--------|-------|--------|---------|------------|\n"
        )

    with TIMING_LOG.open("a") as f:
        f.write(row + "\n")

    print(f"Timing log updated: {row}")

if __name__ == "__main__":
    main()
