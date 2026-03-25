# Tiered screen config — copy to screens/<topic>.py and fill in CONFIGS.
#
# Run with:
#   python3 infra/tiered_screen.py --screen screens/<topic>.py [--ladder quick|standard|thorough]
#
# Rules:
#   - First entry must always be the baseline with overrides={}
#   - desc: one sentence explaining what the change tests and why
#   - overrides: keys must match FULL dict in infra/tiered_screen.py
#
# Optional: set WHY = "..." to add a rationale block to the report header.

WHY = "One sentence explaining why these candidates were chosen."

CONFIGS = [
    ("baseline",
     "Control — no changes.",
     {}),

    ("my_variant",
     "One sentence: what changes and what hypothesis it tests.",
     {"mlp_act": "swiglu"}),

    # ("another", "Description.", {"attnres_mode": "value_residual"}),
]
