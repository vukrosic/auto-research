import os
import sys
import torch

# Add the parent directory to sys.path to allow importing from train_gpt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from train_gpt import GPT, Hyperparameters

def count_parameters(model):
    return sum(p.numel() for p in model.parameters())

configs = [
    {"NAME": "L10_D448_H8_KV8_M2", "L": 10, "D": 448, "H": 8, "KV": 8, "M": 2},
    {"NAME": "L9_D480_H8_KV8_M2", "L": 9, "D": 480, "H": 8, "KV": 8, "M": 2},
    {"NAME": "L12_D448_H8_KV8_M1", "L": 12, "D": 448, "H": 8, "KV": 8, "M": 1},
    {"NAME": "L15_D384_H6_KV6_M2", "L": 15, "D": 384, "H": 6, "KV": 6, "M": 2},
    {"NAME": "L20_D320_H5_KV5_M2", "L": 20, "D": 320, "H": 5, "KV": 5, "M": 2},
]

for cfg in configs:
    try:
        model = GPT(
            vocab_size=1024,
            num_layers=cfg["L"],
            model_dim=cfg["D"],
            num_heads=cfg["H"],
            num_kv_heads=cfg["KV"],
            mlp_mult=cfg["M"],
            tie_embeddings=True,
            tied_embed_init_std=0.005,
            logit_softcap=30.0,
            rope_base=10000.0,
            qk_gain_init=1.5
        )
        params = count_parameters(model)
        actual_est = params * 0.856
        print(f"{cfg['NAME']}: {params:,} params (~{actual_est/1e6:.2f} MB)")
    except Exception as e:
        print(f"{cfg['NAME']}: Error: {e}")
