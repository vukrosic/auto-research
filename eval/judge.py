"""Scoring logic for LLM eval benchmarks.

Validates LLM responses against test case expectations:
- Action block parsing and validation
- Menu selection validation against CATEGORIES
- Override validation against VALID_OVERRIDES
- Instruction following checks
- Response quality heuristics
"""
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.experiment_menu import CATEGORIES
from api.actions import VALID_OVERRIDES, ACTION_HANDLERS

ACTION_PATTERN = re.compile(r"\[ACTION\]\s*(\{.*?\})\s*\[/ACTION\]", re.DOTALL)

SCORE_WEIGHTS = {
    "action_valid": 0.30,
    "schema_correct": 0.20,
    "pipeline_runs": 0.25,
    "instruction_follow": 0.15,
    "response_quality": 0.10,
}


@dataclass
class JudgeResult:
    test_id: str
    model_id: str
    scores: dict = field(default_factory=dict)      # dimension -> 0.0-1.0
    details: dict = field(default_factory=dict)      # dimension -> explanation
    weighted_total: float = 0.0
    passed: bool = False
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "model_id": self.model_id,
            "scores": self.scores,
            "details": self.details,
            "weighted_total": round(self.weighted_total, 4),
            "passed": self.passed,
        }


def parse_actions(text: str) -> list[dict]:
    """Extract all [ACTION] JSON blocks from LLM response."""
    actions = []
    for match in ACTION_PATTERN.finditer(text):
        try:
            data = json.loads(match.group(1))
            actions.append(data)
        except json.JSONDecodeError:
            actions.append({"_parse_error": match.group(1)[:200]})
    return actions


def validate_selections(configs: list[dict]) -> tuple[bool, list[str]]:
    """Check that all menu selections reference real categories and options."""
    errors = []
    for i, cfg in enumerate(configs):
        sels = cfg.get("selections", {})
        for cat_id, opt_id in sels.items():
            if cat_id not in CATEGORIES:
                errors.append(f"Config {i} ({cfg.get('name', '?')}): unknown category '{cat_id}'")
            elif opt_id not in CATEGORIES[cat_id]["options"]:
                errors.append(f"Config {i} ({cfg.get('name', '?')}): unknown option '{opt_id}' in '{cat_id}'")
    return len(errors) == 0, errors


def validate_overrides(variants: list[dict]) -> tuple[bool, list[str]]:
    """Check that raw overrides use valid parameter names."""
    errors = []
    for i, v in enumerate(variants):
        overrides = v.get("overrides", {})
        for key in overrides:
            if key not in VALID_OVERRIDES:
                errors.append(f"Variant {i} ({v.get('name', '?')}): invalid override '{key}'")
    return len(errors) == 0, errors


def _check_numbered_list(text: str, min_count: int) -> tuple[bool, int]:
    """Check if response contains a numbered list with at least min_count items."""
    pattern = re.compile(r"^\s*(\d+)[.)]\s", re.MULTILINE)
    numbers = [int(m.group(1)) for m in pattern.finditer(text)]
    if not numbers:
        return False, 0
    return max(numbers) >= min_count, max(numbers)


def _check_mentions(text: str, keywords: list[str]) -> tuple[bool, list[str]]:
    """Check if response mentions all required keywords (case-insensitive)."""
    text_lower = text.lower()
    missing = [kw for kw in keywords if kw.lower() not in text_lower]
    return len(missing) == 0, missing


def _check_asks_confirmation(text: str) -> bool:
    """Check if response asks user to confirm before running."""
    confirm_patterns = [
        r"\brun\b", r"\bstart\b", r"\blaunch\b", r"\bgo\b",
        r"\bready\b", r"\bconfirm\b", r"\bshall\b", r"\bwant me to\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in confirm_patterns)


def _check_refuses_lr(text: str) -> bool:
    """Check if response refuses learning rate tuning."""
    text_lower = text.lower()
    refusal_signals = [
        "learning rate" in text_lower and any(w in text_lower for w in ["can't", "won't", "don't", "not", "forbidden", "architecture"]),
        "lr tuning" in text_lower and "not" in text_lower,
        "architecture changes only" in text_lower,
        "forbidden" in text_lower,
    ]
    return any(refusal_signals)


def _word_count(text: str) -> int:
    return len(text.split())


def judge(test_case: dict, model_id: str, response: str, pipeline_ran: bool = False) -> JudgeResult:
    """Score a single LLM response against test case expectations.

    Args:
        test_case: From test_cases.py
        model_id: Which model produced this response
        response: The LLM's raw text response
        pipeline_ran: Whether the pipeline was actually executed (for pipeline_runs score)

    Returns:
        JudgeResult with per-dimension scores and weighted total
    """
    expect = test_case.get("expect", {})
    actions = parse_actions(response)
    has_action = len(actions) > 0
    result = JudgeResult(
        test_id=test_case["id"],
        model_id=model_id,
        raw_response=response,
    )

    # ── action_valid ──────────────────────────────────────────────────
    action_score = 1.0
    action_detail = "OK"

    if expect.get("no_action"):
        if has_action:
            action_score = 0.0
            action_detail = "Emitted [ACTION] when it should not have"
        else:
            action_detail = "Correctly did not emit [ACTION]"

    elif expect.get("no_action_or_knowledge_action"):
        if has_action:
            if all(a.get("type") == "knowledge" for a in actions if "_parse_error" not in a):
                action_score = 1.0
                action_detail = "Emitted knowledge action (acceptable)"
            else:
                action_score = 0.5
                action_detail = "Emitted non-knowledge action for a knowledge question"
        else:
            action_detail = "Answered inline without action (acceptable)"

    elif expect.get("has_action"):
        if not has_action:
            action_score = 0.0
            action_detail = "Missing [ACTION] block"
        else:
            action = actions[0]
            if "_parse_error" in action:
                action_score = 0.2
                action_detail = f"Invalid JSON: {action['_parse_error'][:100]}"
            elif expect.get("action_type") and action.get("type") != expect["action_type"]:
                action_score = 0.5
                action_detail = f"Wrong action type: got '{action.get('type')}', expected '{expect['action_type']}'"
            else:
                action_detail = f"Valid {action.get('type', '?')} action"

    result.scores["action_valid"] = action_score
    result.details["action_valid"] = action_detail

    # ── schema_correct ────────────────────────────────────────────────
    schema_score = 1.0
    schema_detail = "OK"

    if has_action and not any("_parse_error" in a for a in actions):
        action = actions[0]
        atype = action.get("type", "")

        if atype == "screen":
            configs = action.get("configs", [])
            valid, errors = validate_selections(configs)
            if not valid:
                schema_score = max(0, 1.0 - len(errors) * 0.15)
                schema_detail = f"{len(errors)} invalid selections: {'; '.join(errors[:3])}"
            else:
                schema_detail = f"All {len(configs)} configs have valid selections"

            # Check required selections if specified
            if expect.get("required_selections"):
                for cat, opt in expect["required_selections"].items():
                    found = any(
                        cfg.get("selections", {}).get(cat) == opt
                        for cfg in configs
                    )
                    if not found:
                        schema_score = max(0, schema_score - 0.2)
                        schema_detail += f"; missing required {cat}={opt}"

        elif atype == "screen_raw":
            variants = action.get("variants", [])
            valid, errors = validate_overrides(variants)
            if not valid:
                schema_score = max(0, 1.0 - len(errors) * 0.2)
                schema_detail = f"{len(errors)} invalid overrides: {'; '.join(errors[:3])}"
            else:
                schema_detail = f"All {len(variants)} variants have valid overrides"

            if expect.get("required_overrides"):
                for key, val in expect["required_overrides"].items():
                    found = any(
                        v.get("overrides", {}).get(key) == val
                        for v in variants
                    )
                    if not found:
                        schema_score = max(0, schema_score - 0.2)
                        schema_detail += f"; missing {key}={val}"

    elif expect.get("has_action") and not has_action:
        schema_score = 0.0
        schema_detail = "No action to validate"

    elif expect.get("no_action") or expect.get("no_action_or_knowledge_action"):
        schema_detail = "N/A (no action expected)"

    result.scores["schema_correct"] = schema_score
    result.details["schema_correct"] = schema_detail

    # ── pipeline_runs ─────────────────────────────────────────────────
    pipeline_score = 1.0
    pipeline_detail = "N/A"

    if expect.get("pipeline_completes"):
        if pipeline_ran:
            pipeline_score = 1.0
            pipeline_detail = "Pipeline executed successfully"
        elif not has_action:
            pipeline_score = 0.0
            pipeline_detail = "No action emitted, pipeline could not run"
        else:
            pipeline_score = 0.5
            pipeline_detail = "Action emitted but pipeline not executed (dry-run)"
    else:
        pipeline_detail = "Pipeline execution not required for this test"

    result.scores["pipeline_runs"] = pipeline_score
    result.details["pipeline_runs"] = pipeline_detail

    # ── instruction_follow ────────────────────────────────────────────
    inst_score = 1.0
    inst_issues = []

    # Config count check
    if expect.get("min_configs") and has_action:
        action = actions[0]
        configs = action.get("configs", action.get("variants", []))
        if len(configs) < expect["min_configs"]:
            penalty = min(0.5, (expect["min_configs"] - len(configs)) * 0.1)
            inst_score -= penalty
            inst_issues.append(f"Only {len(configs)} configs (need {expect['min_configs']}+)")

    # Confirmation check
    if expect.get("asks_confirmation"):
        if not _check_asks_confirmation(response):
            inst_score -= 0.3
            inst_issues.append("Didn't ask for confirmation before running")

    # LR refusal check
    if expect.get("refuses_lr"):
        if not _check_refuses_lr(response):
            inst_score -= 0.5
            inst_issues.append("Did not refuse learning rate tuning")

    # Numbered list check
    if expect.get("contains_numbered_list"):
        has_list, count = _check_numbered_list(response, expect.get("min_ideas", 10))
        if not has_list:
            inst_score -= 0.4
            inst_issues.append(f"Numbered list has {count} items (need {expect.get('min_ideas', 10)}+)")

    # Mentions check
    if expect.get("mentions"):
        all_found, missing = _check_mentions(response, expect["mentions"])
        if not all_found:
            inst_score -= 0.2 * len(missing)
            inst_issues.append(f"Missing keywords: {missing}")

    inst_score = max(0, inst_score)
    result.scores["instruction_follow"] = inst_score
    result.details["instruction_follow"] = "; ".join(inst_issues) if inst_issues else "All instructions followed"

    # ── response_quality ──────────────────────────────────────────────
    quality_score = 1.0
    quality_issues = []

    # Word count check
    if expect.get("max_words"):
        wc = _word_count(response)
        if wc > expect["max_words"]:
            quality_score -= 0.3
            quality_issues.append(f"Too long: {wc} words (max {expect['max_words']})")

    # Follow-up suggestions
    if expect.get("suggests_followup"):
        followup_signals = ["try", "next", "follow", "curious", "wonder", "what if", "could"]
        if not any(s in response.lower() for s in followup_signals):
            quality_score -= 0.3
            quality_issues.append("No follow-up suggestions")

    # Basic personality check (has emoji, not too dry)
    if not expect.get("no_action"):
        # Only check personality for conversational responses
        pass  # Keeping this lightweight — personality is hard to auto-judge

    quality_score = max(0, quality_score)
    result.scores["response_quality"] = quality_score
    result.details["response_quality"] = "; ".join(quality_issues) if quality_issues else "OK"

    # ── Weighted total ────────────────────────────────────────────────
    result.weighted_total = sum(
        result.scores.get(dim, 0) * weight
        for dim, weight in SCORE_WEIGHTS.items()
    )
    result.passed = result.weighted_total >= 0.6

    return result
