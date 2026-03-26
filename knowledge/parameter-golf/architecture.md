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
- **Embedding bottleneck size matters (2026-03-26, 500 steps, SKIP_QUANT_EVAL)**:
  - bn128 (baseline): 1.6673 BPB
  - bn192: 1.6649 BPB (-0.0024)
  - bn256: 1.6632 BPB (-0.0041)
  - Clear monotonic improvement: 128 is too small, larger bottleneck = better
  - bn320: 1.6566 BPB (-0.0107) — larger delta than 128→256 combined! trend accelerating
  - Next: validate bn320 at 4k steps, explore bn384 (= full dim)
- MoE4e d384 is highly consistent across seeds (Δ=0.0004)
- QAT alone is within noise (+/-0.003 BPB), does not hurt MoE

## Leaderboard State (2026-03-26)
- **Leader: 1.1194 BPB** by @abaybektursun (merged 2026-03-23)
  - 11L, d512, 8 heads, 4 KV heads (NOT MoE — dense, fits via int6 quantization)
  - LeakyReLU(0.5)² + Legal Score-First TTT + Parallel Muon
  - BigramHash(1536) vocabulary, Partial RoPE (16 of 64 dims)
  - XSA (cross-sequence attention) on last 4 layers
  - GPTQ-lite int6 + lzma compression
  - EMA(0.997) + SWA every 50 steps
- **N-gram cache revolution** (unmerged, legality debated):
  - 0.1663 BPB with learned 7-expert softmax gate + frozen n-gram oracle
  - Pure neural track capped ~1.11-1.12 BPB
- **Key gap analysis vs our 1.3564:**
  - We use MoE4e at d384 (wider effective model but lower base dim)
  - Leader uses dense 11L d512 + int6 quant (more params via better compression)
  - Missing: BigramHash vocab, XSA, TTT, EMA/SWA, int6 quant, partial RoPE

## Constraints
- Submission limit: 16 MB (int8 zlib-compressed; leader uses int6+lzma)
- Must train in <10min on 8xH100s
- Competition deadline: 2026-04-30
- Our current gap: 1.3564 → 1.1194 = 0.237 BPB
