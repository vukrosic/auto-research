WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('leaky05_safe', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('swiglu_safe', '⚡ Activation Function: swiglu, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'swiglu', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'embed_bottleneck': 128, 'tie_embeddings': False}),
]
