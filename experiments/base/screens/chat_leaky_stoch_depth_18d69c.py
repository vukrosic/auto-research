WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('leaky_stoch01', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1}),
    ('leaky_stoch02', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2}),
    ('leaky_stoch01_moe4', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('leaky_stoch02_moe4', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('leaky_stoch01_deep12', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 📏 Model Depth: 12L', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'num_layers': 12}),
    ('leaky_stoch02_deep12', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02, 📏 Model Depth: 12L', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2, 'num_layers': 12}),
    ('leaky_stoch01_untied', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('leaky_stoch02_untied', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02, 📝 Embedding Strategy: untied_bn128', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2, 'embed_bottleneck': 128, 'tie_embeddings': False}),
    ('leaky_stoch01_moe4_wide', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('leaky_stoch02_wide', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2}),
]
