#!/usr/bin/env python3
"""
Visual queue runner for tiny (~3M param) ablation experiments on 3090.

Usage:
    python3 infra/run_queue_tiny.py                             # run queues/active.txt
    python3 infra/run_queue_tiny.py --test                      # run ONLY first exp, check timing
    python3 infra/run_queue_tiny.py --verify                    # test timing + test wallclock cap
    python3 infra/run_queue_tiny.py --dry-run                   # print plan, no execution
    python3 infra/run_queue_tiny.py --start 15                  # resume from exp #15
    cp queues/archive/tiny/tiny50_followup_best.txt queues/active.txt
    python3 infra/run_queue_tiny.py queues/active.txt

Expected per-experiment: ~100s (1.7min)
Hard limits enforced:
  1. MAX_WALLCLOCK_SECONDS=90  → train_gpt.py stops training cleanly, runs final eval
  2. OUTER_TIMEOUT_S=145       → Python subprocess kill if train_gpt.py hangs
"""

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── Timing thresholds ─────────────────────────────────────────────────────────
# Current 3090 reality for this queue is closer to ~90-110s/experiment:
# ~50-60s training + long final val, with heavier combos clustering near ~100s.
# INT8 eval is SKIPPED: runner kills process once val_bpb appears in log
EXPECTED_S       = 100   # expected wall time per experiment (seconds)
WARN_S           = 120   # yellow warning: running slow
OVER_S           = 150   # red: clearly overtime
OUTER_TIMEOUT    = 180   # hard kill fallback if process hangs
KILL_AFTER_VAL_S = 4     # seconds to wait after val_bpb logged before killing (skip int8)

# ── ANSI ─────────────────────────────────────────────────────────────────────
R = "\033[0m"
BOLD = "\033[1m"; DIM = "\033[2m"
RED = "\033[31m"; YLW = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"; MAG = "\033[35m"

def c(code, text): return f"{code}{text}{R}"

REPO = Path(__file__).parent.parent
ACTIVE_QUEUE = (REPO / "queues" / "active.txt").resolve()
LOG_STEP_RE = re.compile(r'^step:(\d+)/(\d+)\s+')
LOG_STEP_AVG_RE = re.compile(r'^step:(\d+)/(\d+).+step_avg:([\d.]+)ms$')
LOG_STEP_VAL_RE = re.compile(r'^step:(\d+)/(\d+)\s+val_loss:[\d.]+\s+val_bpb:([\d.]+)')
LOG_FINAL_VAL_RE = re.compile(r'^final_int8_zlib_roundtrip_exact\s+val_loss:[\d.]+\s+val_bpb:([\d.]+)')


# ── Queue parsing ─────────────────────────────────────────────────────────────

def parse_queue(path: str) -> list[dict]:
    exps = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name, steps_str = parts[0], parts[1]
            env = {}
            for p in parts[2:]:
                if p.startswith('#'):
                    break
                k, _, v = p.partition('=')
                if k:
                    env[k] = v
            exps.append({"name": name, "steps": int(steps_str), "env": env})
    return exps


def is_done(name: str) -> bool:
    return (REPO / "results" / name / "train.log").exists()


def persist_artifacts(name: str, log_path: str, env: dict) -> None:
    """Backfill result artifacts even when the runner exits early after val_bpb."""
    result_dir = REPO / "results" / name
    result_dir.mkdir(parents=True, exist_ok=True)

    src_log = Path(log_path)
    if not src_log.is_absolute():
        src_log = REPO / src_log

    if src_log.exists():
        shutil.copy2(src_log, result_dir / "train.log")

    subprocess.run(
        [
            sys.executable,
            "infra/export_experiment_artifacts.py",
            "--run-id", name,
            "--log-path", str(src_log),
            "--output-dir", str(result_dir),
        ],
        env=env,
        cwd=str(REPO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def terminate_process_group(proc: subprocess.Popen) -> None:
    """Terminate the whole experiment process group, not just the shell wrapper."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def kill_process_group(proc: subprocess.Popen) -> None:
    """Hard-kill the whole experiment process group."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


# ── Log parsing ───────────────────────────────────────────────────────────────

def _last_match(path: str, pattern: str) -> Optional[re.Match]:
    try:
        lines = Path(path).read_text(errors='replace').splitlines()
        for line in reversed(lines):
            m = re.search(pattern, line)
            if m:
                return m
    except FileNotFoundError:
        pass
    return None


def get_val_bpb(log_path: str) -> Optional[float]:
    try:
        lines = Path(log_path).read_text(errors='replace').splitlines()
        for line in reversed(lines):
            m = LOG_STEP_VAL_RE.match(line)
            if m:
                return float(m.group(3))
        for line in reversed(lines):
            m = LOG_FINAL_VAL_RE.match(line)
            if m:
                return float(m.group(1))
    except FileNotFoundError:
        pass
    return None


def get_last_step(log_path: str) -> tuple[Optional[int], Optional[int]]:
    try:
        lines = Path(log_path).read_text(errors='replace').splitlines()
        for line in reversed(lines):
            m = LOG_STEP_RE.match(line)
            if m:
                return (int(m.group(1)), int(m.group(2)))
    except FileNotFoundError:
        pass
    return (None, None)


def get_step_avg_ms(log_path: str) -> Optional[float]:
    """Latest step_avg from log (ms per training step)."""
    try:
        lines = Path(log_path).read_text(errors='replace').splitlines()
        for line in reversed(lines):
            m = LOG_STEP_AVG_RE.match(line)
            if m:
                return float(m.group(3))
    except FileNotFoundError:
        pass
    return None


def detect_failure(log_path: str) -> Optional[str]:
    """Return a short error description if the log shows a crash."""
    try:
        text = Path(log_path).read_text(errors='replace')
        if 'nan' in text.lower() or 'NaN' in text:
            return "NaN in loss"
        if 'RuntimeError' in text or 'CUDA error' in text:
            for line in text.splitlines():
                if 'RuntimeError' in line or 'CUDA error' in line:
                    return line.strip()[:80]
    except FileNotFoundError:
        pass
    return None


# ── Experiment runner ─────────────────────────────────────────────────────────

def run_experiment(
    exp: dict,
    log_path: str,
    display_idx: int,
    total: int,
) -> dict:
    """
    Run one experiment. Prints live status. Returns result dict.
    """
    name = exp["name"]
    steps = exp["steps"]
    env = {**os.environ, **exp["env"]}

    (REPO / "results" / name).mkdir(parents=True, exist_ok=True)
    (REPO / "logs").mkdir(exist_ok=True)

    cmd = ["bash", "infra/run_experiment.sh", name, str(steps)]
    # run_experiment.sh always writes the live log to logs/<run_id>.txt via tee.
    # Use that canonical path for parsing/progress even in verify mode.
    log_file = REPO / "logs" / f"{name}.txt"
    if log_file.exists():
        log_file.unlink()
    live_log_path = str(log_file)

    # Header
    print(f"\n{c(BOLD, f'[{display_idx:02d}/{total}]')} {c(CYN, name)}")
    BASE_DEFS = {
        "NUM_LAYERS":"6","MODEL_DIM":"256","NUM_HEADS":"4","NUM_KV_HEADS":"2",
        "MLP_MULT":"2","TRAIN_BATCH_TOKENS":"65536","VAL_LOSS_EVERY":"0",
        "WARMUP_STEPS":"10","WARMDOWN_ITERS":"50","MAX_WALLCLOCK_SECONDS":"75",
        "VAL_BATCH_SIZE":"4194304",
    }
    extras = {k: v for k, v in exp["env"].items() if BASE_DEFS.get(k) != v}
    if extras:
        print(f"  {c(DIM, ' '.join(f'{k}={v}' for k, v in extras.items()))}")
    else:
        print(f"  {c(DIM, '(base config)')}")

    start = time.time()
    timed_out = False
    killed_after_val = False

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        cwd=str(REPO),
        start_new_session=True,
    )

    POLL = 3  # seconds between status polls
    warned_overtime = False
    val_done_at: Optional[float] = None   # time when val_bpb first appeared

    while True:
        try:
            proc.wait(timeout=POLL)
            break  # finished naturally
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start

            if elapsed >= OUTER_TIMEOUT:
                kill_process_group(proc)
                proc.wait()
                timed_out = True
                break

            # ── Early kill: skip int8 eval ─────────────────────────────────
            # Once training is done AND val_bpb is logged, kill to skip int8.
            cur_step, tot_step = get_last_step(live_log_path)
            current_val_bpb = get_val_bpb(live_log_path)
            if val_done_at is None and current_val_bpb is not None:
                val_done_at = time.time()
            if val_done_at is not None and (time.time() - val_done_at) >= KILL_AFTER_VAL_S:
                terminate_process_group(proc)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    kill_process_group(proc)
                    proc.wait()
                killed_after_val = True
                break  # cleanly killed after val

            # Build status line
            elapsed_str = f"{elapsed:.0f}s"

            if elapsed >= OVER_S:
                if not warned_overtime:
                    warned_overtime = True
                    print(f"\n  {c(RED, '⚠ OVERTIME')} — experiment is running longer than {OVER_S}s")
                elapsed_color = c(RED, f"⚠ {elapsed_str}")
            elif elapsed >= WARN_S:
                elapsed_color = c(YLW, f"~ {elapsed_str}")
            else:
                elapsed_color = elapsed_str

            step_info = ""
            if cur_step is not None:
                pct = cur_step / tot_step * 100 if tot_step else 0
                step_info = f"  step {cur_step}/{tot_step} ({pct:.0f}%)"

            bar_done = int(elapsed / EXPECTED_S * 20)
            bar_done = min(bar_done, 20)
            bar = "█" * bar_done + "░" * (20 - bar_done)
            bar_color = c(RED if elapsed >= OVER_S else (YLW if elapsed >= WARN_S else GRN), bar)

            print(f"  ▶ [{bar_color}] {elapsed_color}{step_info}    ", end='\r', flush=True)

    elapsed = time.time() - start
    val_bpb = get_val_bpb(live_log_path)
    cur_step, tot_step = get_last_step(live_log_path)
    step_avg = get_step_avg_ms(live_log_path)
    exit_code = proc.returncode
    # Don't flag as failure if we intentionally killed after val_bpb
    if killed_after_val:
        exit_code = 0
    failure = detect_failure(live_log_path) if exit_code != 0 else None
    persist_artifacts(name, live_log_path, env)

    # Final result line
    print(" " * 70, end='\r')  # clear progress line

    if timed_out:
        status = c(RED, f"TIMEOUT ({elapsed:.0f}s — subprocess killed)")
    elif exit_code != 0:
        err = failure or f"exit={exit_code}"
        status = c(RED, f"FAILED ({err}) in {elapsed:.0f}s")
    elif val_bpb is None:
        status = c(YLW, f"NO VAL_BPB in {elapsed:.0f}s")
    elif elapsed >= OVER_S:
        status = c(YLW, f"SLOW {elapsed:.0f}s (>{OVER_S}s expected)")
    else:
        status = c(GRN, f"✓ {elapsed:.0f}s")

    bpb_str = f"val_bpb={c(BOLD, f'{val_bpb:.4f}')}" if val_bpb else "val_bpb=N/A"
    step_str = (f"steps={cur_step}/{tot_step}" if cur_step else "")
    ms_str = (f"  {step_avg:.0f}ms/step" if step_avg else "")

    print(f"  {status} | {bpb_str} | {step_str}{ms_str}")

    return {
        "name": name,
        "elapsed": elapsed,
        "val_bpb": val_bpb,
        "step_done": cur_step,
        "step_total": tot_step,
        "step_avg_ms": step_avg,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "failure": failure,
    }


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(results: list[dict], prefix=""):
    if not results:
        return
    ok = [r for r in results if r["val_bpb"] is not None]
    failed = [r for r in results if r["val_bpb"] is None]
    slow = [r for r in results if r["elapsed"] >= WARN_S and r["val_bpb"] is not None]
    timed = [r for r in results if r["timed_out"]]

    print(f"\n  {c(DIM, '─' * 62)}")
    print(f"  {c(BOLD, prefix + 'Summary:')}")
    print(f"  Done: {len(results)}  |  "
          f"OK: {c(GRN, str(len(ok)))}  |  "
          f"Failed: {c(RED, str(len(failed)))}  |  "
          f"Slow: {c(YLW, str(len(slow)))}  |  "
          f"Timeout: {c(RED, str(len(timed)))}")

    if ok:
        best = min(ok, key=lambda r: r["val_bpb"])
        worst = max(ok, key=lambda r: r["val_bpb"])
        avg_time = sum(r["elapsed"] for r in results) / len(results)
        best_bpb = f"{best['val_bpb']:.4f}"
        worst_bpb = f"{worst['val_bpb']:.4f}"
        print(f"  Best:  {c(GRN, best_bpb)} — {best['name']}")
        print(f"  Worst: {c(YLW, worst_bpb)} — {worst['name']}")
        print(f"  Avg time: {avg_time:.0f}s/exp | Total: {sum(r['elapsed'] for r in results)/60:.1f}min")

    if failed:
        print(f"  {c(RED, 'Failures:')} " + ", ".join(r['name'] for r in failed[:5]))

    print(f"  {c(DIM, '─' * 62)}")


def print_top_n(results: list[dict], n=10):
    ok = sorted([r for r in results if r["val_bpb"] is not None], key=lambda r: r["val_bpb"])
    if not ok:
        return
    print(f"\n  {c(BOLD, f'Top {min(n, len(ok))} by val_bpb:')}")
    for i, r in enumerate(ok[:n], 1):
        steps_str = f"  ({r['step_done']}/{r['step_total']} steps)" if r['step_done'] else ""
        bpb_s = f"{r['val_bpb']:.4f}"
        print(f"  {i:2d}. {c(GRN, bpb_s)}  {r['name']:<30}{steps_str}")


def print_queue_progress(results: list[dict], completed: int, total: int, elapsed_s: float):
    if not results:
        return
    avg_s = sum(r["elapsed"] for r in results) / len(results)
    remaining = max(total - completed, 0)
    eta_s = remaining * avg_s
    ok = [r for r in results if r["val_bpb"] is not None]
    best = min(ok, key=lambda r: r["val_bpb"]) if ok else None
    best_str = f"{best['name']} {best['val_bpb']:.4f}" if best else "N/A"
    print(
        f"  Queue progress: {completed}/{total} done | "
        f"avg {avg_s:.0f}s/exp | elapsed {elapsed_s/60:.1f}min | "
        f"ETA ~{eta_s/60:.0f}min | best {best_str}"
    )


def write_progress_snapshot(
    queue_file: str,
    total: int,
    skipped: int,
    results: list[dict],
    elapsed_s: float,
    latest: Optional[dict] = None,
    finished: bool = False,
):
    avg_s = sum(r["elapsed"] for r in results) / len(results) if results else None
    completed = skipped + len(results)
    remaining = max(total - completed, 0)
    ok = [r for r in results if r["val_bpb"] is not None]
    best = min(ok, key=lambda r: r["val_bpb"]) if ok else None
    snapshot = {
        "queue_file": queue_file,
        "queue_name": Path(queue_file).stem,
        "updated_at_epoch_s": time.time(),
        "finished": finished,
        "total_experiments": total,
        "skipped_existing": skipped,
        "completed_total": completed,
        "completed_this_run": len(results),
        "remaining": remaining,
        "elapsed_s": elapsed_s,
        "avg_elapsed_s": avg_s,
        "eta_s": remaining * avg_s if avg_s is not None else None,
        "latest_result": latest,
        "best_result": best,
    }
    out_path = REPO / "logs" / f"queue_progress_{Path(queue_file).stem}.json"
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")


# ── Verify mode ───────────────────────────────────────────────────────────────

def run_verify(queue_file: str):
    """
    Two-part verification:
      Test A: timing — baseline should finish in ~100s
      Test B: wallclock cap — MAX_WALLCLOCK_SECONDS=5 should stop early with val_bpb reported
    """
    print(c(BOLD, "\n══════════════════════════════════════════════════════════════"))
    print(c(BOLD, "  VERIFICATION MODE"))
    print(c(BOLD, "══════════════════════════════════════════════════════════════"))

    exps = parse_queue(queue_file)
    baseline = exps[0]

    # ── Test A: timing ──────────────────────────────────────────────────────
    print(f"\n{c(BOLD, 'Test A: Timing')} — expect ~{EXPECTED_S}s for baseline")
    print(f"  Config: {baseline['env'].get('NUM_LAYERS','?')}L "
          f"{baseline['env'].get('MODEL_DIM','?')}d "
          f"batch={baseline['env'].get('TRAIN_BATCH_TOKENS','?')} "
          f"steps={baseline['steps']}  MAX_WALLCLOCK={baseline['env'].get('MAX_WALLCLOCK_SECONDS','?')}s")

    r_a = run_experiment(baseline, "logs/verify_timing.txt", 1, 2)

    if r_a["timed_out"]:
        print(c(RED, "  ✗ OUTER TIMEOUT — something is very wrong (hung process)"))
    elif r_a["val_bpb"] is None:
        print(c(RED, "  ✗ No val_bpb — training script may have crashed"))
    elif r_a["elapsed"] > WARN_S:
        print(c(YLW, f"  ⚠ Slow: {r_a['elapsed']:.0f}s (expected ~{EXPECTED_S}s). "
                     f"100 exps would take ~{100*r_a['elapsed']/3600:.1f}hr"))
    elif r_a["elapsed"] < 60:
        print(c(YLW, f"  ⚠ Very fast: {r_a['elapsed']:.0f}s — might be using cached results?"))
    else:
        print(c(GRN, f"  ✓ Timing OK: {r_a['elapsed']:.0f}s  "
                     f"| 100 exps ≈ {100*r_a['elapsed']/3600:.1f}hr"))
        if r_a["step_avg_ms"]:
            print(f"    Step speed: {r_a['step_avg_ms']:.0f}ms/step "
                  f"(expected ~161ms)")

    # ── Test B: wallclock cap ───────────────────────────────────────────────
    print(f"\n{c(BOLD, 'Test B: Wallclock cap')} — MAX_WALLCLOCK_SECONDS=5 should stop early")
    print("  Training at ~161ms/step → should reach ~30 steps before cap triggers")

    cap_exp = {
        "name": "verify_wcap_test",
        "steps": 500,
        "env": {
            **baseline["env"],
            "MAX_WALLCLOCK_SECONDS": "5",
        }
    }

    r_b = run_experiment(cap_exp, "logs/verify_wcap.txt", 2, 2)

    if r_b["timed_out"]:
        print(c(RED, "  ✗ OUTER TIMEOUT — wallclock cap did not stop training!"))
    elif r_b["val_bpb"] is None:
        print(c(RED, "  ✗ No val_bpb after early stop — final eval did not run"))
    elif r_b["step_done"] is not None and r_b["step_done"] >= 490:
        print(c(YLW, f"  ⚠ Ran {r_b['step_done']}/500 steps — cap may not have triggered "
                     f"(total time: {r_b['elapsed']:.0f}s)"))
    elif r_b["step_done"] is not None and r_b["step_done"] < 100:
        print(c(GRN, f"  ✓ Wallclock cap works: stopped at step {r_b['step_done']}/500 "
                     f"in {r_b['elapsed']:.0f}s | val_bpb={r_b['val_bpb']:.4f}"))
    else:
        print(c(GRN, f"  ✓ Stopped at step {r_b['step_done']}/500 "
                     f"in {r_b['elapsed']:.0f}s | val_bpb={r_b['val_bpb']:.4f}"))

    # ── Verdict ─────────────────────────────────────────────────────────────
    timing_ok = r_a["val_bpb"] is not None and not r_a["timed_out"] and r_a["elapsed"] < WARN_S
    cap_ok = r_b["val_bpb"] is not None and not r_b["timed_out"] and (
        r_b["step_done"] is None or r_b["step_done"] < 200
    )

    print()
    if timing_ok and cap_ok:
        print(c(GRN, "  ✓ ALL CHECKS PASSED — ready to run full queue"))
        print(f"    Run: python3 infra/run_queue_tiny.py {queue_file}")
    else:
        if not timing_ok:
            print(c(YLW, "  ⚠ Timing check: issues detected — review before full run"))
        if not cap_ok:
            print(c(RED, "  ✗ Wallclock cap: NOT working as expected!"))


# ── Dry run ───────────────────────────────────────────────────────────────────

def run_dry(exps: list[dict]):
    skip = sum(1 for e in exps if is_done(e["name"]))
    run = len(exps) - skip
    print(c(BOLD, f"\n  DRY RUN — {len(exps)} experiments | {skip} done | {run} to run"))
    print(f"  Est time: ~{run * EXPECTED_S / 60:.0f}min (~{run * EXPECTED_S / 3600:.1f}hr)\n")

    BASE_DEFAULTS = {
        "NUM_LAYERS": "6", "MODEL_DIM": "256", "NUM_HEADS": "4", "NUM_KV_HEADS": "2",
        "MLP_MULT": "2", "TRAIN_BATCH_TOKENS": "65536", "VAL_LOSS_EVERY": "500",
        "WARMUP_STEPS": "10", "WARMDOWN_ITERS": "50", "MAX_WALLCLOCK_SECONDS": "90",
    }

    for i, exp in enumerate(exps, 1):
        done_marker = c(GRN, "✓") if is_done(exp["name"]) else c(DIM, "○")
        diffs = {k: v for k, v in exp["env"].items() if BASE_DEFAULTS.get(k) != v}
        extras_str = " ".join(f"{k}={v}" for k, v in diffs.items()) or c(DIM, "(base)")
        print(f"  {done_marker} [{i:03d}] {exp['name']:<30}  {extras_str}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Visual queue runner for tiny-model ablations"
    )
    ap.add_argument(
        "queue_file",
        nargs="?",
        default="queues/active.txt",
        help="Only queues/active.txt is allowed; copy archived queues there first",
    )
    ap.add_argument("--test",     action="store_true", help="Run first experiment only")
    ap.add_argument("--verify",   action="store_true", help="Run timing + wallclock cap tests")
    ap.add_argument("--dry-run",  action="store_true", help="Print plan, no execution")
    ap.add_argument("--start",    type=int, default=1,  help="Resume from experiment N (1-indexed)")
    ap.add_argument("--only",     type=str, default=None, help="Run only this experiment name")
    ap.add_argument("--summary-every", type=int, default=10)
    args = ap.parse_args()

    os.chdir(REPO)

    requested_queue = Path(args.queue_file)
    if not requested_queue.is_absolute():
        requested_queue = (REPO / requested_queue).resolve()
    else:
        requested_queue = requested_queue.resolve()

    if requested_queue != ACTIVE_QUEUE:
        print(c(RED, "  ERROR: only queues/active.txt may be executed."))
        print("  Copy any archived or proposed batch into queues/active.txt first.")
        sys.exit(1)

    exps = parse_queue(str(ACTIVE_QUEUE))
    total = len(exps)
    skip_n = sum(1 for e in exps if is_done(e["name"]))
    queue_name = ACTIVE_QUEUE.name

    # ── Banner ─────────────────────────────────────────────────────────────
    print(c(BOLD, "\n╔══════════════════════════════════════════════════════════════╗"))
    print(c(BOLD,  "║  TINY QUEUE RUNNER                                           ║"))
    print(c(BOLD,  "╚══════════════════════════════════════════════════════════════╝"))
    print(f"  Queue : queues/active.txt ({queue_name})")
    print(f"  Total : {total} experiments | {c(GRN, str(skip_n))} done | "
          f"{c(CYN, str(total - skip_n))} to run")
    print(f"  Est   : ~{(total-skip_n)*EXPECTED_S/60:.0f}min "
          f"(~{(total-skip_n)*EXPECTED_S/3600:.1f}hr)")
    print(f"  Limits: MAX_WALLCLOCK=75s (training) | kill after val_bpb (skip int8) | outer={OUTER_TIMEOUT}s")
    print(f"  Timing: ~{EXPECTED_S}s/exp expected | {c(YLW,f'>{WARN_S}s=slow')} | {c(RED,f'>{OVER_S}s=overtime')}")

    if args.dry_run:
        run_dry(exps)
        return

    if args.verify:
        run_verify(str(ACTIVE_QUEUE))
        return

    # ── Select experiments to run ─────────────────────────────────────────
    if args.only:
        run_list = [e for e in exps if e["name"] == args.only]
        if not run_list:
            print(c(RED, f"  ERROR: experiment '{args.only}' not found in queue"))
            sys.exit(1)
        print(f"\n  Running single experiment: {args.only}")
    elif args.test:
        run_list = exps[:1]
        print(f"\n{c(YLW, '  TEST MODE')} — running first experiment only")
        print(f"  After this, verify timing and run full queue if OK.")
    elif args.start > 1:
        run_list = exps[args.start - 1:]
        print(f"\n  Resuming from experiment #{args.start}")
    else:
        run_list = exps

    print()

    # ── Run loop ──────────────────────────────────────────────────────────
    results = []
    run_n = 0
    t_start = time.time()
    write_progress_snapshot(args.queue_file, total, skip_n, results, 0.0)

    for exp in run_list:
        actual_idx = exps.index(exp) + 1

        if is_done(exp["name"]):
            print(f"[{actual_idx:02d}/{total}] {c(DIM, exp['name'] + ' — done, skipping')}")
            continue

        run_n += 1
        result = run_experiment(
            exp,
            f"logs/{exp['name']}.txt",
            actual_idx,
            total,
        )
        results.append(result)
        elapsed_s = time.time() - t_start
        write_progress_snapshot(args.queue_file, total, skip_n, results, elapsed_s, latest=result)
        print_queue_progress(results, skip_n + len(results), total, elapsed_s)

        # Periodic summary
        if run_n % args.summary_every == 0:
            remaining = len([e for e in run_list[run_list.index(exp)+1:]
                             if not is_done(e["name"])])
            print_summary(results, prefix=f"After {run_n} — ")
            if remaining > 0:
                eta_s = remaining * (sum(r["elapsed"] for r in results) / len(results))
                print(f"  ETA: ~{eta_s/60:.0f}min remaining  "
                      f"({remaining} experiments left)\n")

    # ── Final output ──────────────────────────────────────────────────────
    total_min = (time.time() - t_start) / 60
    print(c(BOLD, "\n╔══════════════════════════════════════════════════════════════╗"))
    print(c(BOLD,  "║  COMPLETE                                                    ║"))
    print(c(BOLD,  "╚══════════════════════════════════════════════════════════════╝"))
    print(f"  Total wall time: {total_min:.1f}min")
    write_progress_snapshot(
        args.queue_file,
        total,
        skip_n,
        results,
        time.time() - t_start,
        latest=results[-1] if results else None,
        finished=True,
    )
    print_summary(results, prefix="Final ")
    print_top_n(results, n=10)

    # ── Problems report ───────────────────────────────────────────────────
    problems = [r for r in results if r["val_bpb"] is None or r["timed_out"] or r["exit_code"] != 0]
    if problems:
        print(f"\n  {c(RED, 'PROBLEMS — needs attention:')}")
        for r in problems:
            tag = "TIMEOUT" if r["timed_out"] else (f"exit={r['exit_code']}" if r["exit_code"] else "no_val_bpb")
            err = f" ({r['failure']})" if r.get("failure") else ""
            print(f"    {c(RED, '●')} {r['name']}  [{tag}]{err}")
    else:
        print(c(GRN, "\n  No problems — all experiments reported val_bpb ✓"))


if __name__ == "__main__":
    main()
