WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('leaky4', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('relu4', '🧠 Mixture of Experts: moe4_d384', {'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('swiglu4', '⚡ Activation Function: swiglu, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'swiglu', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('abs4', '⚡ Activation Function: abs2, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'abs2', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('leaky4_deep', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, 📏 Model Depth: 12L', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_layers': 12}),
    ('leaky4_wide', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim640', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 640, 'num_heads': 10, 'num_kv_heads': 5}),
    ('leaky4_untied', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('leaky4_stoch', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe4_d384, 🛡️ Regularization: stoch_depth_01', {'mlp_act': 'leaky_relu2_05', 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'stoch_depth_rate': 0.1}),
    ('leaky2_moe2', '⚡ Activation Function: leaky05, 🧠 Mixture of Experts: moe2', {'mlp_act': 'leaky_relu2_05', 'num_experts': 2}),
    ('swiglu_moe2', '⚡ Activation Function: swiglu, 🧠 Mixture of Experts: moe2', {'mlp_act': 'swiglu', 'num_experts': 2}),
]
