"""Test cases — only requests that result in experiments running end-to-end.

Each test is a multi-turn conversation:
  Turn 1: user describes what they want
  Turn 2: assistant shows plan ({{model_response}} = captured from turn 1)
  Turn 3: user confirms ("run" / "go" / "yes")

The final LLM response must emit a valid [ACTION] block that executes
tiered_screen.py via the pipeline.
"""

# All test cases use the "debug" ladder (1→1 steps) so they finish in seconds.
LADDER = "debug"

TEST_CASES = [
    # ── Direct activation requests ───────────────────────────────────────
    {
        "id": "activation_leaky",
        "description": "User wants leaky relu tournament",
        "turns": [
            {"role": "user", "content": "let's try different activation functions, I'm curious about leaky relu"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "activation_swiglu",
        "description": "User specifically asks for swiglu",
        "turns": [
            {"role": "user", "content": "swiglu looks promising, can we test it?"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "go"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "activation_all",
        "description": "User wants to compare all activation options",
        "turns": [
            {"role": "user", "content": "run a full activation function comparison, all of them"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "yes"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },

    # ── MoE requests ─────────────────────────────────────────────────────
    {
        "id": "moe_basic",
        "description": "User wants to try mixture of experts",
        "turns": [
            {"role": "user", "content": "I want to test mixture of experts"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "start it"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "moe_vs_dense",
        "description": "User wants MoE vs dense comparison",
        "turns": [
            {"role": "user", "content": "does MoE actually help? compare it against dense models"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run it"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },

    # ── Embeddings requests ───────────────────────────────────────────────
    {
        "id": "embeddings_untied",
        "description": "User wants to test embedding strategies",
        "turns": [
            {"role": "user", "content": "let's test untied embeddings vs tied, I want to see the difference"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run it"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "embeddings_bottleneck",
        "description": "User asks about embedding bottleneck sizes",
        "turns": [
            {"role": "user", "content": "compare different embedding bottleneck sizes"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "launch"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },

    # ── Architecture/size requests ────────────────────────────────────────
    {
        "id": "depth_comparison",
        "description": "User wants to test different layer counts",
        "turns": [
            {"role": "user", "content": "test shallow vs deep models — how does depth affect things?"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "go"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "width_comparison",
        "description": "User wants to test different model widths",
        "turns": [
            {"role": "user", "content": "compare dim384 vs dim512 vs dim640"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "weight_sharing",
        "description": "User asks about weight sharing / cycle blocks",
        "turns": [
            {"role": "user", "content": "can we reuse layer weights to save params? try cycling"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "yes run it"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },

    # ── Combo / multi-component requests ─────────────────────────────────
    {
        "id": "combo_leaky_moe",
        "description": "User wants leaky relu + MoE combo",
        "turns": [
            {"role": "user", "content": "combine leaky relu with MoE 4 experts"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "combo_best_known",
        "description": "User asks to test around the best known config",
        "turns": [
            {"role": "user", "content": "let's explore variations around the best config you know"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "go"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "combo_attention_variants",
        "description": "User asks about attention mechanisms",
        "turns": [
            {"role": "user", "content": "test value residual attention combined with other tricks"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "start"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },

    # ── Raw/custom override requests ──────────────────────────────────────
    {
        "id": "raw_custom_dim",
        "description": "User wants a non-menu dimension",
        "turns": [
            {"role": "user", "content": "try model_dim=448 with 7 layers"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {"has_action": True, "action_type": "screen_raw", "overrides_valid": True, "pipeline_completes": True},
    },
    {
        "id": "raw_stoch_depth",
        "description": "User asks to test stochastic depth rates",
        "turns": [
            {"role": "user", "content": "test stochastic_depth_rate at 0.05, 0.1, 0.15, 0.2"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "yes do it"},
        ],
        "expect": {"has_action": True, "pipeline_completes": True},
    },

    # ── Vague / open-ended requests ───────────────────────────────────────
    {
        "id": "vague_improve",
        "description": "User gives vague 'make it better' request",
        "turns": [
            {"role": "user", "content": "I want to improve the model, what should we try?"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "sounds good, run option 1"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "vague_wild_idea",
        "description": "User gives a vague wild-card request",
        "turns": [
            {"role": "user", "content": "try something weird and unexpected that hasn't been done"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run it"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
    {
        "id": "vague_number_pick",
        "description": "User picks a number from the welcome list",
        "turns": [
            {"role": "user", "content": "hi what should I try"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "3"},
            {"role": "assistant", "content": "{{model_response}}"},
            {"role": "user", "content": "run"},
        ],
        "expect": {"has_action": True, "action_type": "screen", "min_configs": 8, "selections_valid": True, "pipeline_completes": True},
    },
]


def get_all_categories() -> list[str]:
    return sorted(set(tc.get("category", "experiment") for tc in TEST_CASES))


def get_cases_by_category(category: str) -> list[dict]:
    return [tc for tc in TEST_CASES if tc.get("category", "experiment") == category]
