WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('moe2_baseline', '🧠 Mixture of Experts: moe2', {'num_experts': 2}),
    ('moe4_baseline', '🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim384', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('moe2_leaky', '🧠 Mixture of Experts: moe2, ⚡ Activation Function: leaky05', {'num_experts': 2, 'mlp_act': 'leaky_relu2_05'}),
    ('moe4_leaky', '🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim384, ⚡ Activation Function: leaky05', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'mlp_act': 'leaky_relu2_05'}),
    ('moe2_wide', '🧠 Mixture of Experts: moe2, ↔️ Model Width: dim640', {'num_experts': 2, 'model_dim': 640, 'num_heads': 10, 'num_kv_heads': 5}),
    ('moe4_deep', '🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim384, 📏 Model Depth: 12L', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_layers': 12}),
    ('moe2_untied', '🧠 Mixture of Experts: moe2, 📝 Embedding Strategy: untied_bn128', {'num_experts': 2, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('moe4_untied', '🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim384, 📝 Embedding Strategy: untied_bn128', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('moe2_stochdepth', '🧠 Mixture of Experts: moe2, 🛡️ Regularization: stoch_depth_02', {'num_experts': 2, 'stoch_depth_rate': 0.2}),
    ('moe4_stochdepth', '🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim384, 🛡️ Regularization: stoch_depth_02', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'stoch_depth_rate': 0.2}),
]
