"""LLM eval benchmark runner — tests whether the model generates valid experiment configs.

All test cases run the full pipeline (tiered_screen.py) using the "debug" ladder
(1→1 steps) so each experiment finishes in seconds.

Usage (from /root/auto-research):
    python -m eval.bench                        # Run all tests, live pipeline
    python -m eval.bench --test activation_leaky # Single test
    python -m eval.bench --dry-run              # JSON/schema validation only, no pipeline
    python -m eval.bench --report               # Compare saved results
    python -m eval.bench --list-tests           # Show all test cases
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.models import MODELS, call_llm, list_available_models, LLMResponse
from eval.test_cases import TEST_CASES, get_cases_by_category, get_all_categories
from eval.judge import judge, parse_actions, JudgeResult, SCORE_WEIGHTS

# Import system prompt from the chat router
from api.routers.chat import SYSTEM_PROMPT, ANALYSIS_PROMPT

RESULTS_DIR = Path(__file__).parent / "results"


def run_single_test(model_id: str, test_case: dict, live: bool = False) -> dict:
    """Run a single test case against a single model.

    For multi-turn tests, runs each turn sequentially, capturing model responses
    to fill in {{model_response}} placeholders.
    """
    turns = test_case["turns"]
    system = SYSTEM_PROMPT

    # Analysis tests use a different system prompt
    if test_case.get("system_override"):
        system = ANALYSIS_PROMPT

    messages = [{"role": "system", "content": system}]
    total_input = 0
    total_output = 0
    total_latency = 0
    total_cost = 0.0
    final_response = ""
    llm_error = ""

    for i, turn in enumerate(turns):
        if turn["role"] == "assistant" and turn["content"] == "{{model_response}}":
            # This is a placeholder — use the model's previous response
            messages.append({"role": "assistant", "content": final_response})
            continue

        messages.append({"role": turn["role"], "content": turn["content"]})

        # Only call LLM on user turns (assistant turns are captured responses)
        if turn["role"] == "user":
            resp = call_llm(model_id, messages, temperature=0.7, max_tokens=2048)

            if resp.error:
                llm_error = resp.error
                break

            final_response = resp.content
            total_input += resp.input_tokens
            total_output += resp.output_tokens
            total_latency += resp.latency_ms
            total_cost += resp.cost_usd

            # Add model response to history for multi-turn
            messages.append({"role": "assistant", "content": resp.content})

    # Run pipeline if live mode and there's an action
    pipeline_ran = False
    pipeline_output = ""
    if live and not llm_error:
        actions = parse_actions(final_response)
        if actions and test_case.get("expect", {}).get("pipeline_completes"):
            from api.actions import dispatch_action
            from eval.test_cases import LADDER
            try:
                for action_data in actions:
                    if "_parse_error" not in action_data:
                        # Force debug ladder so screens finish in seconds
                        action_data["ladder"] = LADDER
                        pipeline_output = dispatch_action(action_data)
                pipeline_ran = True
            except Exception as e:
                llm_error = f"Pipeline error: {e}"

    # Judge the final response
    if llm_error:
        result = JudgeResult(
            test_id=test_case["id"],
            model_id=model_id,
            scores={dim: 0.0 for dim in SCORE_WEIGHTS},
            details={dim: f"LLM error: {llm_error}" for dim in SCORE_WEIGHTS},
            weighted_total=0.0,
            passed=False,
            raw_response=final_response,
        )
    else:
        result = judge(test_case, model_id, final_response, pipeline_ran=pipeline_ran)

    return {
        **result.to_dict(),
        "category": test_case.get("category", "experiment"),
        "description": test_case.get("description", ""),
        "usage": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "latency_ms": total_latency,
            "cost_usd": round(total_cost, 6),
        },
        "pipeline_ran": pipeline_ran,
        "error": llm_error,
    }


def run_benchmark(model_id: str, test_cases: list[dict], live: bool = False) -> dict:
    """Run all test cases for a single model. Returns full benchmark result."""
    print(f"\n{'='*60}")
    print(f"  Benchmarking: {model_id}")
    print(f"  Tests: {len(test_cases)} | Mode: {'LIVE' if live else 'DRY-RUN'}")
    print(f"{'='*60}\n")

    results = []
    for i, tc in enumerate(test_cases, 1):
        print(f"  [{i}/{len(test_cases)}] {tc['id']}...", end=" ", flush=True)
        t0 = time.time()
        result = run_single_test(model_id, tc, live=live)
        elapsed = time.time() - t0

        status = "PASS" if result["passed"] else "FAIL"
        score = result["weighted_total"]
        print(f"{status} ({score:.0%}) [{elapsed:.1f}s]")

        if result["error"]:
            print(f"    ERROR: {result['error'][:100]}")

        results.append(result)

    # Aggregate
    total_cost = sum(r["usage"]["cost_usd"] for r in results)
    total_latency = sum(r["usage"]["latency_ms"] for r in results)
    avg_score = sum(r["weighted_total"] for r in results) / len(results) if results else 0
    pass_rate = sum(1 for r in results if r["passed"]) / len(results) if results else 0

    # Per-category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"scores": [], "passed": 0, "total": 0}
        categories[cat]["scores"].append(r["weighted_total"])
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    category_summary = {}
    for cat, data in categories.items():
        category_summary[cat] = {
            "avg_score": round(sum(data["scores"]) / len(data["scores"]), 4),
            "pass_rate": round(data["passed"] / data["total"], 4),
            "passed": data["passed"],
            "count": data["total"],
        }

    # Per-dimension averages
    dimension_avgs = {}
    for dim in SCORE_WEIGHTS:
        scores = [r["scores"].get(dim, 0) for r in results]
        dimension_avgs[dim] = round(sum(scores) / len(scores), 4) if scores else 0

    benchmark = {
        "model_id": model_id,
        "timestamp": datetime.now().isoformat(),
        "mode": "live" if live else "dry-run",
        "test_count": len(results),
        "avg_score": round(avg_score, 4),
        "pass_rate": round(pass_rate, 4),
        "total_cost_usd": round(total_cost, 6),
        "total_latency_ms": total_latency,
        "dimension_averages": dimension_avgs,
        "category_summary": category_summary,
        "results": results,
    }

    # Print summary
    print(f"\n{'─'*60}")
    print(f"  {model_id} Summary")
    print(f"{'─'*60}")
    print(f"  Avg Score: {avg_score:.1%}  |  Pass Rate: {pass_rate:.1%}")
    print(f"  Cost: ${total_cost:.4f}  |  Latency: {total_latency}ms")
    print(f"\n  Per-dimension:")
    for dim, avg in dimension_avgs.items():
        print(f"    {dim:20s}: {avg:.1%}")
    print(f"\n  Per-category:")
    for cat, data in category_summary.items():
        print(f"    {cat:20s}: {data['avg_score']:.1%} ({data['passed']}/{data['count']} passed)")
    print()

    return benchmark


def save_result(benchmark: dict):
    """Save benchmark result to eval/results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = benchmark["model_id"].replace("/", "_").replace("-", "_")
    path = RESULTS_DIR / f"{ts}_{model_slug}.json"
    path.write_text(json.dumps(benchmark, indent=2))
    print(f"  Saved: {path}")
    return path


def generate_report():
    """Generate a comparison report from all saved results."""
    result_files = sorted(RESULTS_DIR.glob("*.json"))
    if not result_files:
        print("No results found in eval/results/. Run benchmarks first.")
        return

    # Load latest result per model
    latest = {}
    for f in result_files:
        data = json.loads(f.read_text())
        mid = data["model_id"]
        if mid not in latest or data["timestamp"] > latest[mid]["timestamp"]:
            latest[mid] = data

    models = sorted(latest.keys())

    lines = [
        f"## LLM Benchmark Results — {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]

    # Main comparison table
    dims = list(SCORE_WEIGHTS.keys())
    header = "| Model | " + " | ".join(d.replace("_", " ").title() for d in dims) + " | TOTAL | Cost |"
    sep = "|-------|" + "|".join("-------:" for _ in dims) + "|------:|-----:|"
    lines.extend([header, sep])

    for mid in models:
        data = latest[mid]
        dim_scores = " | ".join(f"{data['dimension_averages'].get(d, 0):.0%}" for d in dims)
        total = f"{data['avg_score']:.0%}"
        cost = f"${data['total_cost_usd']:.4f}"
        lines.append(f"| {mid} | {dim_scores} | {total} | {cost} |")

    lines.append("")

    # Per-category breakdown
    all_cats = set()
    for data in latest.values():
        all_cats.update(data.get("category_summary", {}).keys())
    all_cats = sorted(all_cats)

    lines.append("### Per-Category Breakdown")
    lines.append("")
    cat_header = "| Category | " + " | ".join(models) + " |"
    cat_sep = "|----------|" + "|".join("------:" for _ in models) + "|"
    lines.extend([cat_header, cat_sep])

    for cat in all_cats:
        scores = []
        for mid in models:
            cs = latest[mid].get("category_summary", {}).get(cat, {})
            scores.append(f"{cs.get('avg_score', 0):.0%}")
        lines.append(f"| {cat} | " + " | ".join(scores) + " |")

    lines.append("")

    # Failure analysis
    lines.append("### Failure Analysis")
    lines.append("")
    for mid in models:
        data = latest[mid]
        failures = [r for r in data.get("results", []) if not r["passed"]]
        if failures:
            lines.append(f"**{mid}** ({len(failures)} failures):")
            for f in failures[:5]:
                detail_parts = [v for v in f.get("details", {}).values() if v not in ("OK", "N/A")]
                detail = "; ".join(detail_parts[:2]) if detail_parts else "low score"
                lines.append(f"- `{f['test_id']}`: {detail}")
            lines.append("")
        else:
            lines.append(f"**{mid}**: All tests passed!")
            lines.append("")

    report = "\n".join(lines)

    # Save report
    report_path = RESULTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report)
    print(report)
    print(f"\nSaved: {report_path}")


def list_tests():
    """Print all test cases grouped by category."""
    for cat in get_all_categories():
        cases = get_cases_by_category(cat)
        print(f"\n{cat} ({len(cases)} tests):")
        for tc in cases:
            print(f"  {tc['id']:30s} — {tc.get('description', '')}")


def main():
    parser = argparse.ArgumentParser(description="LLM eval benchmark for auto-research chatbot")
    parser.add_argument("--model", type=str, help="Run only this model (default: all available)")
    parser.add_argument("--category", type=str, help="Run only this test category")
    parser.add_argument("--test", type=str, action="append", help="Run specific test ID (repeat for multiple)")
    parser.add_argument("--dry-run", action="store_true", help="Skip pipeline execution — only validate JSON/schema")
    parser.add_argument("--report", action="store_true", help="Generate comparison report from saved results")
    parser.add_argument("--list-models", action="store_true", help="List all models and availability")
    parser.add_argument("--list-tests", action="store_true", help="List all test cases")

    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    if args.list_models:
        available = list_available_models()
        for mid, cfg in MODELS.items():
            status = "READY" if mid in available else f"MISSING {cfg['api_key_env']}"
            print(f"  {mid:20s} [{status}]")
        return

    if args.list_tests:
        list_tests()
        return

    # Select models
    if args.model:
        if args.model not in MODELS:
            print(f"Unknown model: {args.model}. Available: {list(MODELS.keys())}")
            sys.exit(1)
        model_ids = [args.model]
    else:
        model_ids = list(MODELS.keys())  # Run all registered models

    # Select test cases
    if args.test:
        test_cases = [tc for tc in TEST_CASES if tc["id"] in args.test]
        if not test_cases:
            print(f"Unknown tests: {args.test}")
            sys.exit(1)
    elif args.category:
        test_cases = get_cases_by_category(args.category)
        if not test_cases:
            print(f"Unknown category: {args.category}. Available: {get_all_categories()}")
            sys.exit(1)
    else:
        test_cases = TEST_CASES

    print(f"Auto-Research LLM Eval Benchmark")
    print(f"Models: {', '.join(model_ids)}")
    print(f"Tests: {len(test_cases)}")
    live = not args.dry_run
    print(f"Mode: {'DRY-RUN (JSON validation only)' if args.dry_run else 'LIVE (pipeline executes with debug ladder)'}")

    for model_id in model_ids:
        benchmark = run_benchmark(model_id, test_cases, live=live)
        save_result(benchmark)

    if len(model_ids) > 1:
        print("\nGenerating comparison report...")
        generate_report()


if __name__ == "__main__":
    main()
