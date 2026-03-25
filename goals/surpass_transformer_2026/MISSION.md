# Mission: Surpass Transformer Architecture (2026)

**Set by**: Human
**Created**: 2026-03-25
**Duration**: 1 year (through March 2027)

## Objective

Push the frontier of small language model architecture beyond current transformer baselines. The vehicle is the [OpenAI Parameter Golf Challenge](https://github.com/openai/parameter-golf): build the best 16 MB language model trained in <10 min on 8xH100s, scored by bits-per-byte (val_bpb, lower = better).

## Measurable Targets

| Target | Metric | Value | Deadline |
|--------|--------|-------|----------|
| Competition baseline | val_bpb | < 1.2244 | April 30, 2026 |
| Stretch | val_bpb | < 1.20 | June 2026 |
| Frontier | val_bpb | Best achievable under 16 MB | March 2027 |

## Scope

- **Project**: parameter-golf (`projects/parameter-golf.json`)
- **Codebase**: `experiments/base/` (train_gpt.py and supporting files)
- **Knowledge base**: `knowledge/parameter-golf/`

## Constraints

- Budget: $40/month GPU spend (adjustable by human)
- Hardware: Whatever GPUs are assigned (see goal's resources.md)
- Size limit: 16 MB submission (int8 zlib-compressed)
- Training time: <10 min on 8xH100s (competition rule)
- No LR-only tuning — architecture/mechanism changes required

## Success Criteria

**Year success**: Beat the competition leaderboard (1.2244 BPB) with a novel architecture change.
**Stretch success**: Achieve state-of-art for the 16 MB regime, potentially with non-transformer components.

## What "Surpass Transformer" Means

This is deliberately ambitious. It doesn't mean replacing the transformer wholesale. It means finding mechanisms — attention variants, routing strategies, activation designs, normalization tricks, or entirely new components — that provably improve over the standard transformer at this scale and budget. Each such mechanism is a research contribution, regardless of competition placement.

## Non-Goals

- Hyperparameter tuning without mechanism insight
- Winning the competition through training tricks alone (schedule, data ordering)
- Producing a paper (nice to have, not required)
