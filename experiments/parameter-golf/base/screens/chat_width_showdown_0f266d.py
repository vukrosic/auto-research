WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('narrow', '↔️ Model Width: dim384, ⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128', {'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('default', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe2, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'num_experts': 2, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('wide', '↔️ Model Width: dim640, ⚡ Activation Function: leaky05, 📝 Embedding Strategy: untied_bn128', {'model_dim': 640, 'num_heads': 10, 'num_kv_heads': 5, 'mlp_act': 'leaky_relu2_05', 'embed_bottleneck': 128, 'tie_embeddings': False}),
]
