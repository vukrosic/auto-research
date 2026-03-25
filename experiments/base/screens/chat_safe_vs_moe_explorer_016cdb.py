WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('safe_bet', '⚡ Activation Function: leaky05, ↔️ Model Width: dim384, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_experts': 4, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('moe_explorer', '⚡ Activation Function: leaky05, ↔️ Model Width: dim384, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128, 🛡️ Regularization: stoch_depth_02', {'mlp_act': 'leaky_relu2_05', 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_experts': 4, 'embed_bottleneck': 128, 'tie_embeddings': False, 'stoch_depth_rate': 0.2}),
]
