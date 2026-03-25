WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('swiglu_3x', '⚡ Activation Function: swiglu, 🔧 MLP Expansion Ratio: 3x', {'mlp_act': 'swiglu', 'mlp_mult': 3}),
]
