WHY = "Test three different residual connection techniques: highway networks, stochastic depth, and value residual attention to see which improves learning most effectively"

CONFIGS = [
    ("baseline", "Control — no changes.", {}),
    ("highway_networks", "Enable highway connections with learned gates", {"highway_net": 1}),
    ("stochastic_depth", "Add stochastic depth with 0.1 drop rate", {"stoch_depth_rate": 0.1}),
    ("value_residual_attention", "Enable value residual attention mode", {"attnres_mode": "value_residual"}),
]
