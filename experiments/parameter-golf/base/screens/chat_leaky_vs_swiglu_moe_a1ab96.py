WHY = "User-designed experiment via chat"

CONFIGS = [
    ("baseline", "Control — all defaults.", {}),
    ('leaky_stoch02_moe4', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('swiglu_stoch02_moe4', '⚡ Activation Function: swiglu, 🛡️ Regularization: stoch_depth_02, 🧠 Mixture of Experts: moe4_d384', {'mlp_act': 'swiglu', 'stoch_depth_rate': 0.2, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3}),
    ('leaky_stoch01_moe4_deep12', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384, 📏 Model Depth: 12L', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_layers': 12}),
    ('swiglu_stoch01_moe4_deep12', '⚡ Activation Function: swiglu, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384, 📏 Model Depth: 12L', {'mlp_act': 'swiglu', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_layers': 12}),
    ('leaky_stoch02_moe4_wide', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_02, 🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim640', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.2, 'num_experts': 4, 'model_dim': 640, 'num_heads': 10, 'num_kv_heads': 5}),
    ('swiglu_stoch02_moe4_wide', '⚡ Activation Function: swiglu, 🛡️ Regularization: stoch_depth_02, 🧠 Mixture of Experts: moe4_d384, ↔️ Model Width: dim640', {'mlp_act': 'swiglu', 'stoch_depth_rate': 0.2, 'num_experts': 4, 'model_dim': 640, 'num_heads': 10, 'num_kv_heads': 5}),
    ('leaky_stoch01_moe4_2block', '⚡ Activation Function: leaky05, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384, ♻️ Weight Sharing: 2block_cycle', {'mlp_act': 'leaky_relu2_05', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_unique_blocks': 2, 'num_cycles': 4}),
    ('swiglu_stoch01_moe4_2block', '⚡ Activation Function: swiglu, 🛡️ Regularization: stoch_depth_01, 🧠 Mixture of Experts: moe4_d384, ♻️ Weight Sharing: 2block_cycle', {'mlp_act': 'swiglu', 'stoch_depth_rate': 0.1, 'num_experts': 4, 'model_dim': 384, 'num_heads': 6, 'num_kv_heads': 3, 'num_unique_blocks': 2, 'num_cycles': 4}),
]
