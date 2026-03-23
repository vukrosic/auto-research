"""Test cases for LLM eval benchmarking.

Each test case is a simulated user interaction with expected outcome criteria.
Multi-turn tests use "{{model_response}}" as placeholder — the runner fills it in
with the actual LLM response from the previous turn.
"""

TEST_CASES = [
    # ── Category 1: Welcome ──────────────────────────────────────────────
    {
        "id": "welcome_hi",
        "category": "welcome",
        "description": "Basic greeting should get welcome + 10 ideas, no action",
        "turns": [{"role": "user", "content": "hi!"}],
        "expect": {
            "no_action": True,
            "contains_numbered_list": True,
            "min_ideas": 10,
        },
    },
    {
        "id": "welcome_hello",
        "category": "welcome",
        "description": "Another greeting variant",
        "turns": [{"role": "user", "content": "hello, what can I do here?"}],
        "expect": {
            "no_action": True,
            "contains_numbered_list": True,
            "min_ideas": 10,
        },
    },
    {
        "id": "welcome_blank",
        "category": "welcome",
        "description": "Empty-ish message should still get welcome",
        "turns": [{"role": "user", "content": "hey"}],
        "expect": {
            "no_action": True,
            "contains_numbered_list": True,
            "min_ideas": 8,
        },
    },

    # ── Category 2: Pick from Menu (no run yet) ─────────────────────────
    {
        "id": "pick_leaky",
        "category": "pick_idea",
        "description": "Picking a specific activation should show plan, not run",
        "turns": [{"role": "user", "content": "I want to try leaky relu"}],
        "expect": {
            "no_action": True,
            "mentions": ["leaky"],
            "asks_confirmation": True,
        },
    },
    {
        "id": "pick_moe",
        "category": "pick_idea",
        "description": "Picking MoE should show plan with dim=384 note",
        "turns": [{"role": "user", "content": "let's test mixture of experts with 4 experts"}],
        "expect": {
            "no_action": True,
            "mentions": ["moe", "384"],
            "asks_confirmation": True,
        },
    },
    {
        "id": "pick_swiglu_deep",
        "category": "pick_idea",
        "description": "Picking a combo idea should show plan",
        "turns": [{"role": "user", "content": "I want to try swiglu with 12 layers"}],
        "expect": {
            "no_action": True,
            "mentions": ["swiglu", "12"],
            "asks_confirmation": True,
        },
    },

    # ── Category 3: Confirm and Run ──────────────────────────────────────
    {
        "id": "run_leaky_screen",
        "category": "confirm_and_run",
        "description": "After picking leaky relu, confirm with 'run' should emit screen action",
        "turns": [
            {"role": "user", "content": "let's try different activation functions"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run it"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen",
            "min_configs": 8,
            "selections_valid": True,
            "pipeline_completes": True,
        },
    },
    {
        "id": "run_moe_screen",
        "category": "confirm_and_run",
        "description": "MoE experiment after confirmation",
        "turns": [
            {"role": "user", "content": "I want to test MoE configurations"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "go"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen",
            "min_configs": 8,
            "selections_valid": True,
            "pipeline_completes": True,
        },
    },
    {
        "id": "run_embeddings_screen",
        "category": "confirm_and_run",
        "description": "Embedding strategy comparison",
        "turns": [
            {"role": "user", "content": "compare tied vs untied embeddings"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "yes do it"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen",
            "min_configs": 8,
            "selections_valid": True,
            "pipeline_completes": True,
        },
    },

    # ── Category 4: Combine Ideas ────────────────────────────────────────
    {
        "id": "combine_leaky_moe_untied",
        "category": "combine",
        "description": "Combine three specific ideas — all must appear in output",
        "turns": [
            {"role": "user", "content": "combine leaky relu with MoE 4 experts and untied embeddings bn128"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen",
            "min_configs": 8,
            "selections_valid": True,
            "required_selections": {
                "activation": "leaky05",
                "moe": "moe4_d384",
                "embeddings": "untied_bn128",
            },
        },
    },
    {
        "id": "combine_swiglu_deep_stoch",
        "category": "combine",
        "description": "Combine swiglu + deep + stochastic depth",
        "turns": [
            {"role": "user", "content": "try swiglu with 12 layers and stochastic depth"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "start"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen",
            "min_configs": 8,
            "selections_valid": True,
            "required_selections": {
                "activation": "swiglu",
                "depth": "12L",
            },
        },
    },

    # ── Category 5: Raw/Custom Overrides ─────────────────────────────────
    {
        "id": "raw_custom_dim",
        "category": "raw_override",
        "description": "Custom dimension not in menu should use screen_raw",
        "turns": [
            {"role": "user", "content": "try model_dim=448 with 7 layers and mlp_mult=3"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen_raw",
            "overrides_valid": True,
            "required_overrides": {"model_dim": 448, "num_layers": 7, "mlp_mult": 3},
        },
    },
    {
        "id": "raw_rope_base",
        "category": "raw_override",
        "description": "Custom rope_base value",
        "turns": [
            {"role": "user", "content": "what if we set rope_base to 50000?"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "yes run it"},
        ],
        "expect": {
            "has_action": True,
            "action_type": "screen_raw",
            "overrides_valid": True,
        },
    },

    # ── Category 6: Knowledge Query ──────────────────────────────────────
    {
        "id": "knowledge_activations",
        "category": "knowledge",
        "description": "Ask what's been tried for activations",
        "turns": [{"role": "user", "content": "what activation functions have been tested?"}],
        "expect": {
            "no_action_or_knowledge_action": True,
            "mentions": ["leaky", "relu"],
        },
    },
    {
        "id": "knowledge_best_config",
        "category": "knowledge",
        "description": "Ask what the best known config is",
        "turns": [{"role": "user", "content": "what's the best config found so far?"}],
        "expect": {
            "no_action_or_knowledge_action": True,
            "mentions": ["moe", "untied"],
        },
    },
    {
        "id": "knowledge_failed",
        "category": "knowledge",
        "description": "Ask about what didn't work",
        "turns": [{"role": "user", "content": "what experiments have failed or didn't help?"}],
        "expect": {
            "no_action_or_knowledge_action": True,
        },
    },

    # ── Category 7: Edge Cases / Guardrails ──────────────────────────────
    {
        "id": "guard_lr_tuning",
        "category": "guardrails",
        "description": "Should refuse learning rate tuning",
        "turns": [{"role": "user", "content": "set the learning rate to 0.001 and run"}],
        "expect": {
            "no_action": True,
            "refuses_lr": True,
        },
    },
    {
        "id": "guard_few_configs",
        "category": "guardrails",
        "description": "Should push back on too few configs",
        "turns": [
            {"role": "user", "content": "just run a single config with leaky relu, nothing else"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {
            "min_configs": 8,
        },
    },
    {
        "id": "guard_invalid_option",
        "category": "guardrails",
        "description": "Should not hallucinate a non-existent menu option",
        "turns": [
            {"role": "user", "content": "try the 'turbo_boost' activation and 'mega_moe' option"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {
            "selections_valid": True,
            "no_hallucinated_options": True,
        },
    },
    {
        "id": "guard_size_awareness",
        "category": "guardrails",
        "description": "Should warn about 16MB limit with large configs",
        "turns": [{"role": "user", "content": "try dim=1024 with 24 layers and 8 experts"}],
        "expect": {
            "mentions": ["16", "fit", "mb"],
        },
    },

    # ── Category 8: Analysis Quality ─────────────────────────────────────
    {
        "id": "analysis_winner",
        "category": "analysis",
        "description": "Given results with a clear winner, should identify it",
        "system_override": True,
        "turns": [
            {"role": "user", "content": (
                "Here are the experiment results:\n\n"
                "## Tiered Screen Results\n"
                "| Config | Stage 1 Loss | Stage 2 Loss | Stage 3 Loss | Delta vs Baseline |\n"
                "|--------|-------------|-------------|-------------|-------------------|\n"
                "| baseline | 4.2310 | 3.8901 | 3.7200 | — |\n"
                "| leaky_moe | 4.1890 | 3.8100 | 3.6500 | -0.0700 |\n"
                "| swiglu_deep | 4.2100 | 3.8800 | 3.7100 | -0.0100 |\n"
                "| abs2_wide | 4.2500 | 3.9200 | 3.7400 | +0.0200 |\n\n"
                "Winner: leaky_moe (-0.0700 vs baseline)"
            )},
        ],
        "expect": {
            "no_action": True,
            "mentions": ["leaky_moe", "winner"],
            "max_words": 250,
            "suggests_followup": True,
        },
    },
    {
        "id": "analysis_no_winner",
        "category": "analysis",
        "description": "All variants lost — should acknowledge and pivot",
        "system_override": True,
        "turns": [
            {"role": "user", "content": (
                "Results:\n"
                "| Config | Delta vs Baseline |\n"
                "|--------|-------------------|\n"
                "| variant_a | +0.0150 |\n"
                "| variant_b | +0.0080 |\n"
                "| variant_c | +0.0230 |\n\n"
                "No configs beat baseline."
            )},
        ],
        "expect": {
            "no_action": True,
            "max_words": 250,
            "suggests_followup": True,
        },
    },
]


def get_cases_by_category(category: str) -> list[dict]:
    return [tc for tc in TEST_CASES if tc["category"] == category]


def get_all_categories() -> list[str]:
    return sorted(set(tc["category"] for tc in TEST_CASES))
