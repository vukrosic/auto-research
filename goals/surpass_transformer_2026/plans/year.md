# Year Plan — Surpass Transformer 2026

**Mission**: Surpass transformer architecture on parameter-golf (16 MB LLM)
**Period**: March 2026 — March 2027
**Generated**: 2026-03-25 (AI)

## Starting Position

- **Current best**: 1.3564 BPB (MoE4e + bn128u + leaky(0.5)² @ d384)
- **Target**: < 1.2244 BPB (competition leaderboard)
- **Gap**: 0.132 BPB (10.8%)
- **Known effective mechanisms**: Squared activations, soft MoE, untied factored embeddings
- **Exhausted directions**: Activation function search, convolutions, tied embeddings

## Phase Plan

### Phase 1: Architecture Exploration (Q2 2026 — Apr/May/Jun)

**Objective**: Find 2-3 new mechanisms that each improve BPB by ≥0.01

Focus on unexplored architectural axes:
- Expert scaling (more MoE experts at smaller dim)
- Depth scaling (more layers, narrower models)
- Attention variants (head config, QK-norm, sparse/linear attention)
- Vocabulary optimization (larger BPE vocab)
- Normalization & residual connection design
- MoE routing variants (hard vs soft, capacity factors)

**Milestone**: Best val_bpb < 1.32 by end of Q2
**Risk**: Architecture changes at this scale may have already been well-explored by competition participants. Mitigation: look at less conventional approaches (non-transformer components, adaptive computation).

### Phase 2: Mechanism Stacking & Optimization (Q3 2026 — Jul/Aug/Sep)

**Objective**: Combine winning mechanisms from Phase 1 and optimize their interaction

Focus on:
- Interaction effects between discovered mechanisms
- Joint optimization of stacked changes
- Quantization-aware design (ensure mechanisms survive int8)
- Training dynamics tuning for the combined architecture
- Parameter budget optimization (every byte under 16 MB matters)

**Milestone**: Best val_bpb < 1.27 by end of Q3
**Risk**: Mechanisms may not stack (common in ML). Mitigation: test combinations early in Phase 1, don't assume additivity.

### Phase 3: Novel Components (Q4 2026 — Oct/Nov/Dec)

**Objective**: Explore non-standard components that could break through the transformer ceiling

Focus on:
- Mixture-of-depths / adaptive computation
- State-space models (Mamba-style) as attention replacements
- Retrieval-augmented or memory-augmented architectures (if feasible at 16 MB)
- Hybrid architectures (transformer + non-transformer blocks)
- Cross-pollination from recent papers

**Milestone**: Best val_bpb < 1.23 by end of Q4
**Risk**: Novel components often fail spectacularly at small scale. Mitigation: test at tiny scale first (tiered screening), abort fast.

### Phase 4: Final Push & Hardening (Q1 2027 — Jan/Feb/Mar)

**Objective**: Maximize competition metric, submit best result

Focus on:
- Final architecture tuning on 8xH100 (competition hardware)
- Quantization optimization
- Training schedule optimization for 10-min budget
- Ensemble insights (even if single model for submission)
- Robustness across seeds

**Milestone**: Best val_bpb < 1.22 (beat leaderboard)

## Annual Milestones

| Quarter | End Date | Target BPB | Improvement Needed | Cumulative |
|---------|----------|-----------|-------------------|------------|
| Q1 (partial) | 2026-03-31 | 1.35 | 0.006 | 0.006 |
| Q2 | 2026-06-30 | 1.32 | 0.030 | 0.036 |
| Q3 | 2026-09-30 | 1.27 | 0.050 | 0.086 |
| Q4 | 2026-12-31 | 1.23 | 0.040 | 0.126 |
| Q1 2027 | 2027-03-31 | 1.22 | 0.010 | 0.136 |

## Resource Assumptions

- 1x RTX 3090 (current) — may scale if budget increases
- $40/month GPU spend
- ~80 GPU-hours/month, ~800 experiments/year
- No human gates on experiment execution
- Full autonomy within policy

## Annual Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Architecture search saturates early | Medium | High | Pivot to novel components (Phase 3) earlier |
| Budget insufficient for full runs | Medium | Medium | Prioritize explores, only full-run validated winners |
| Competition baseline gets beaten by others, target moves | Low | Low | Focus on own improvement, not relative position |
| GPU provider changes pricing/availability | Medium | Medium | Design experiments to be GPU-agnostic |
| Mechanisms don't stack | High | High | Test combinations throughout, not just in Phase 2 |

## Open Strategic Questions

- How much of the 0.132 BPB gap is architecture vs training efficiency?
- Is the leaderboard result achievable on 1x3090 at all, or is 8xH100 scaling essential?
- Should we invest in literature review automation to find more ideas?
- At what point should we request additional GPU budget?

---

## Updates

*(Append quarterly reviews below this line)*
