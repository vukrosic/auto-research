#!/usr/bin/env python3
"""Compare micro-lane calibration runs and recommend promotions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RUN_RE = re.compile(r"^micro_(nano|micro)_(.+)$")
KNOWN_POSITIVES = ("embed_bn128_untied", "moe_2e", "moe_4e")
KNOWN_NEGATIVES = ("embed_bn128_tied", "conv_k5")
CONTROL_IDEAS = KNOWN_POSITIVES + KNOWN_NEGATIVES


@dataclass
class RunRecord:
    name: str
    rung: str
    idea: str
    val_bpb: float
    step: int
    max_steps: int
    step_avg_ms: float | None
    gpu_name: str | None
    log_path: str | None
    contaminated: list[str]
    summary_path: str


def load_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_step_avg_ms(log_text: str) -> float | None:
    matches = re.findall(r"step_avg:([0-9.]+)ms", log_text)
    return float(matches[-1]) if matches else None


def count_python_processes(log_text: str) -> int:
    if "Processes:" not in log_text:
        return 0
    section = log_text.split("Processes:", 1)[1]
    lines: list[str] = []
    for line in section.splitlines():
        if line.startswith("===================================================================================================="):
            break
        lines.append(line)
    return sum(1 for line in lines if "python" in line)


def sign(value: float, *, zero_eps: float = 1e-12) -> int:
    if value > zero_eps:
        return 1
    if value < -zero_eps:
        return -1
    return 0


def resolve_log_path(repo_root: Path, summary_path: Path, metadata: dict | None) -> Path | None:
    if isinstance(metadata, dict):
        raw = metadata.get("log_path")
        if isinstance(raw, str) and raw.strip():
            candidate = repo_root / raw
            if candidate.exists():
                return candidate
    fallback = repo_root / "logs" / f"{summary_path.parent.name}.txt"
    return fallback if fallback.exists() else None


def contamination_reasons(log_text: str, step: int, max_steps: int) -> list[str]:
    reasons: list[str] = []
    if re.search(r"OutOfMemoryError|CUDA out of memory", log_text):
        reasons.append("oom")
    if count_python_processes(log_text) > 1:
        reasons.append("shared_gpu")
    if max_steps > 0 and step < max_steps:
        reasons.append("incomplete")
    return reasons


def record_from_summary(summary_path: Path, repo_root: Path) -> RunRecord | None:
    name = summary_path.parent.name
    match = RUN_RE.match(name)
    if not match:
        return None
    summary = load_json(summary_path)
    if summary is None:
        return None
    metadata = load_json(summary_path.parent / "metadata.json")
    rung, idea = match.groups()
    last_eval = summary.get("last_eval") or {}
    final_quant = summary.get("final_quant_eval") or {}
    step = int(last_eval.get("step") or last_eval.get("max_steps") or 0)
    max_steps = int(last_eval.get("max_steps") or last_eval.get("step") or 0)
    val_bpb = final_quant.get("val_bpb") or last_eval.get("val_bpb")
    if val_bpb is None:
        return None
    log_path = resolve_log_path(repo_root, summary_path, metadata)
    log_text = load_text(log_path) if log_path is not None else ""
    gpu_name = None
    if isinstance(metadata, dict):
        gpu_name = (((metadata.get("hardware") or {}).get("gpu") or {}).get("name"))
    return RunRecord(
        name=name,
        rung=rung,
        idea=idea,
        val_bpb=float(val_bpb),
        step=step,
        max_steps=max_steps,
        step_avg_ms=extract_step_avg_ms(log_text),
        gpu_name=str(gpu_name) if gpu_name else None,
        log_path=str(log_path) if log_path is not None else None,
        contaminated=contamination_reasons(log_text, step, max_steps),
        summary_path=str(summary_path),
    )


def load_micro_runs(results_root: Path, repo_root: Path) -> dict[str, dict[str, RunRecord]]:
    runs: dict[str, dict[str, RunRecord]] = {"nano": {}, "micro": {}}
    for summary_path in sorted(results_root.glob("**/summary.json")):
        record = record_from_summary(summary_path, repo_root)
        if record is None:
            continue
        runs.setdefault(record.rung, {})[record.idea] = record
    return runs


def load_reference_run(results_root: Path, repo_root: Path, name: str) -> dict | None:
    direct = results_root / name / "summary.json"
    summary_path = direct if direct.exists() else None
    if summary_path is None:
        for candidate in sorted(results_root.glob(f"**/{name}/summary.json")):
            summary_path = candidate
            break
    if summary_path is None:
        return None
    summary = load_json(summary_path)
    metadata = load_json(summary_path.parent / "metadata.json")
    if summary is None:
        return None
    last_eval = summary.get("last_eval") or {}
    log_path = resolve_log_path(repo_root, summary_path, metadata)
    log_text = load_text(log_path) if log_path is not None else ""
    gpu_name = None
    if isinstance(metadata, dict):
        gpu_name = (((metadata.get("hardware") or {}).get("gpu") or {}).get("name"))
    return {
        "name": name,
        "gpu_name": str(gpu_name) if gpu_name else None,
        "step": int(last_eval.get("step") or last_eval.get("max_steps") or 0),
        "max_steps": int(last_eval.get("max_steps") or last_eval.get("step") or 0),
        "step_avg_ms": extract_step_avg_ms(log_text),
        "contaminated": contamination_reasons(
            log_text,
            int(last_eval.get("step") or last_eval.get("max_steps") or 0),
            int(last_eval.get("max_steps") or last_eval.get("step") or 0),
        ),
        "summary_path": str(summary_path),
    }


def build_report(runs: dict[str, dict[str, RunRecord]], reference_run: dict | None) -> dict:
    baselines: dict[str, RunRecord] = {}
    excluded_runs: list[dict] = []
    usable_runs: list[dict] = []
    for rung in ("nano", "micro"):
        baseline = runs.get(rung, {}).get("baseline")
        if baseline is None:
            raise RuntimeError(f"missing baseline for rung {rung}")
        baselines[rung] = baseline
        for record in runs.get(rung, {}).values():
            payload = asdict(record)
            if record.contaminated:
                excluded_runs.append(payload)
            else:
                usable_runs.append(payload)

    analyses: list[dict] = []
    all_ideas = sorted(set(runs.get("nano", {})) | set(runs.get("micro", {})))
    for idea in all_ideas:
        if idea == "baseline":
            continue
        nano = runs.get("nano", {}).get(idea)
        micro = runs.get("micro", {}).get(idea)
        nano_delta = None
        micro_delta = None
        reasons: list[str] = []
        if nano is None:
            reasons.append("missing_nano")
        elif nano.contaminated:
            reasons.extend([f"nano:{reason}" for reason in nano.contaminated])
        else:
            nano_delta = nano.val_bpb - baselines["nano"].val_bpb
        if micro is None:
            reasons.append("missing_micro")
        elif micro.contaminated:
            reasons.extend([f"micro:{reason}" for reason in micro.contaminated])
        else:
            micro_delta = micro.val_bpb - baselines["micro"].val_bpb
        score = micro_delta + 0.5 * nano_delta if nano_delta is not None and micro_delta is not None else None
        sign_agreement = None
        if nano_delta is not None and micro_delta is not None:
            sign_agreement = sign(nano_delta) == sign(micro_delta)
        analyses.append({
            "idea": idea,
            "nano_delta": nano_delta,
            "micro_delta": micro_delta,
            "score": score,
            "sign_agreement": sign_agreement,
            "excluded_reasons": reasons,
        })

    usable_analyses = [item for item in analyses if item["nano_delta"] is not None and item["micro_delta"] is not None]
    usable_by_idea = {item["idea"]: item for item in usable_analyses}

    positives_present = [usable_by_idea[item] for item in KNOWN_POSITIVES if item in usable_by_idea]
    negatives_present = [usable_by_idea[item] for item in KNOWN_NEGATIVES if item in usable_by_idea]
    micro_positive_wins = all(item["micro_delta"] < 0 for item in positives_present) and len(positives_present) == len(KNOWN_POSITIVES)
    negatives_lose_both = all(item["micro_delta"] > 0 and item["nano_delta"] > 0 for item in negatives_present) and len(negatives_present) == len(KNOWN_NEGATIVES)
    micro_separated = False
    if len(positives_present) == len(KNOWN_POSITIVES) and len(negatives_present) == len(KNOWN_NEGATIVES):
        micro_separated = max(item["micro_delta"] for item in positives_present) < min(item["micro_delta"] for item in negatives_present)

    micro_ranked = sorted(
        [item for item in analyses if item["micro_delta"] is not None],
        key=lambda item: (item["micro_delta"], item["idea"]),
    )
    micro_top3 = [item["idea"] for item in micro_ranked[:3]]
    top3_recall = sum(1 for idea in KNOWN_POSITIVES if idea in micro_top3)

    nano_control_flips = 0
    nano_missed_known_positives = 0
    for idea in CONTROL_IDEAS:
        item = usable_by_idea.get(idea)
        if item is None:
            continue
        expected = -1 if idea in KNOWN_POSITIVES else 1
        actual = sign(item["nano_delta"])
        if actual != expected:
            nano_control_flips += 1
            if idea in KNOWN_POSITIVES:
                nano_missed_known_positives += 1

    sign_agreement_items = [item["sign_agreement"] for item in usable_analyses if item["sign_agreement"] is not None]
    sign_agreement_rate = (
        sum(1 for value in sign_agreement_items if value) / len(sign_agreement_items)
        if sign_agreement_items
        else None
    )

    micro_baseline = baselines["micro"]
    speed_ratio = None
    speed_gate = False
    speed_note = "reference unavailable"
    if (
        reference_run
        and not reference_run["contaminated"]
        and micro_baseline.step_avg_ms is not None
        and reference_run["step_avg_ms"] is not None
        and reference_run["gpu_name"] == micro_baseline.gpu_name
    ):
        speed_ratio = reference_run["step_avg_ms"] / micro_baseline.step_avg_ms
        speed_gate = speed_ratio >= 2.0
        speed_note = "same-gpu comparison"
    elif reference_run and reference_run["gpu_name"] != micro_baseline.gpu_name:
        speed_note = "reference gpu does not match micro baseline gpu"

    hard_pass = sorted(
        [item for item in usable_analyses if item["micro_delta"] <= -0.010],
        key=lambda item: (item["micro_delta"], item["score"], item["idea"]),
    )
    hard_fail = {
        item["idea"]
        for item in usable_analyses
        if item["nano_delta"] >= 0.015 and item["micro_delta"] >= 0.010
    }
    remaining = sorted(
        [
            item
            for item in usable_analyses
            if item["idea"] not in {entry["idea"] for entry in hard_pass}
            and item["idea"] not in hard_fail
            and item["micro_delta"] <= 0.0
            and item["nano_delta"] <= 0.005
        ],
        key=lambda item: (item["score"], item["micro_delta"], item["idea"]),
    )
    promotions = list(hard_pass[:4])
    for item in remaining:
        if len(promotions) >= 4:
            break
        promotions.append(item)
    promoted_ids = {item["idea"] for item in promotions}
    close_call_candidate = None
    if promotions:
        last_promoted = promotions[-1]
        for item in remaining:
            if item["idea"] in promoted_ids:
                continue
            if abs(item["micro_delta"] - last_promoted["micro_delta"]) <= 0.005:
                close_call_candidate = item
                break

    adopt_both = (
        micro_positive_wins
        and negatives_lose_both
        and top3_recall >= 2
        and speed_gate
        and nano_missed_known_positives <= 1
        and nano_control_flips <= 2
    )
    adopt_micro_only = (
        micro_positive_wins
        and len(negatives_present) == len(KNOWN_NEGATIVES)
        and all(item["micro_delta"] > 0 for item in negatives_present)
        and top3_recall >= 2
        and micro_separated
        and (nano_missed_known_positives > 1 or nano_control_flips > 2)
    )
    abort_lane = not micro_separated
    if adopt_both:
        lane_decision = "adopt_both_rungs"
    elif adopt_micro_only:
        lane_decision = "adopt_micro_only"
    elif abort_lane:
        lane_decision = "abort_micro_lane"
    else:
        lane_decision = "needs_manual_review"

    return {
        "baselines": {rung: asdict(record) for rung, record in baselines.items()},
        "reference_run": reference_run,
        "excluded_runs": excluded_runs,
        "usable_runs": usable_runs,
        "ideas": analyses,
        "metrics": {
            "sign_agreement_rate": sign_agreement_rate,
            "micro_top3": micro_top3,
            "top3_positive_recall": top3_recall,
            "nano_control_flips": nano_control_flips,
            "nano_missed_known_positives": nano_missed_known_positives,
            "micro_speed_ratio_vs_reference": speed_ratio,
            "micro_speed_gate_pass": speed_gate,
            "micro_speed_gate_note": speed_note,
            "micro_positive_wins": micro_positive_wins,
            "negative_controls_lose_both": negatives_lose_both,
            "micro_separated": micro_separated,
        },
        "promotion_recommendations": {
            "promotions": promotions,
            "hard_fail": sorted(hard_fail),
            "close_call_candidate": close_call_candidate,
        },
        "lane_decision": lane_decision,
    }


def format_text(report: dict) -> str:
    lines = []
    lines.append(f"lane_decision: {report['lane_decision']}")
    metrics = report["metrics"]
    lines.append(f"sign_agreement_rate: {metrics['sign_agreement_rate']}")
    lines.append(f"micro_top3: {', '.join(metrics['micro_top3']) if metrics['micro_top3'] else '(none)'}")
    lines.append(f"top3_positive_recall: {metrics['top3_positive_recall']}/3")
    lines.append(f"nano_control_flips: {metrics['nano_control_flips']}")
    lines.append(f"nano_missed_known_positives: {metrics['nano_missed_known_positives']}")
    lines.append(f"micro_speed_ratio_vs_reference: {metrics['micro_speed_ratio_vs_reference']}")
    lines.append(f"micro_speed_gate_note: {metrics['micro_speed_gate_note']}")
    lines.append("")
    lines.append("promotions:")
    for item in report["promotion_recommendations"]["promotions"]:
        lines.append(
            f"  - {item['idea']}: nano_delta={item['nano_delta']:.4f} "
            f"micro_delta={item['micro_delta']:.4f} score={item['score']:.4f}"
        )
    if report["promotion_recommendations"]["close_call_candidate"]:
        item = report["promotion_recommendations"]["close_call_candidate"]
        lines.append(
            f"close_call_candidate: {item['idea']} "
            f"(nano_delta={item['nano_delta']:.4f}, micro_delta={item['micro_delta']:.4f})"
        )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--results-root", type=Path, default=None)
    parser.add_argument("--reference-run", default="scale_med_9L384_500")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    results_root = (args.results_root or (repo_root / "results")).resolve()
    runs = load_micro_runs(results_root, repo_root)
    if not any(runs.values()):
        print("no micro_* runs found", file=sys.stderr)
        return 1
    reference_run = load_reference_run(results_root, repo_root, args.reference_run)
    report = build_report(runs, reference_run)
    if args.format == "text":
        print(format_text(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
