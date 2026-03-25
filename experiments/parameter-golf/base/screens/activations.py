WHY = "Testing top activation candidates from KNOWLEDGE.md and prior tiny-model screens."

CONFIGS = [
    ("baseline",   "Control — relu2, no changes.",                   {}),
    ("swiglu",     "SwiGLU — won tiny screen, honest gain at full.",  {"mlp_act": "swiglu"}),
    ("leaky",      "leaky_relu2_05 — best in 60+ KNOWLEDGE.md runs.", {"mlp_act": "leaky_relu2_05"}),
]
