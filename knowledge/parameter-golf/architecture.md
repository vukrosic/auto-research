# Architecture Knowledge — Parameter Golf

## Current Best
- MoE4e + bn128u + leaky(0.5)² at d384: 1.3564 BPB (4k steps, post-quant)
- 9L GPT, 384-dim, 6 heads, 3 KV heads, 4 soft experts
- Untied factored embeddings (bottleneck 128)
- 15.2M params, 14.3 MB submission (under 16 MB limit)

## Proven Facts
- Squaring the activation is the single most impactful design choice
- MoE 4 > 3 >> 2 experts. Jump from 2→4 worth ~0.04 BPB at 500 steps
- MoE4e only fits at dim=384 or below (dim=512 → 24.7 MB, too large)
- dim=400 offers no advantage over dim=384 for MoE4e
- Untied factored embeddings (bn128) are the best legal architecture change: -0.031 BPB
- Tied factored embeddings are catastrophic (+0.058 to +0.379 BPB)
- MoE4e d384 is highly consistent across seeds (Δ=0.0004)
- QAT alone is within noise (+/-0.003 BPB), does not hurt MoE

## Constraints
- Submission limit: 16 MB (int8 zlib-compressed)
- Must train in <10min on 8xH100s
- Leaderboard baseline: 1.2244 BPB
- Target: <1.2194 BPB (beat leaderboard by ≥0.005)
