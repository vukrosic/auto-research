# GPU Step Timing Benchmarks

All measurements use the default 9-layer / 512-dim / 8-head / 4-KV-head setup with batch 524,288 tokens. On single-GPU runs this means `grad_accum=8`; the legacy L40S measurements span multiple activation experiments on that same base config.

## Cost-Efficiency Ranking (cost per step, lower = better)

1. **RTX 5090 ($0.30)** — $0.050/1k steps — fastest single-GPU AND cheapest per step!
2. **RTX 3090 (spot $0.10)** — $0.073/1k steps — still great value, 4x slower
3. **Legacy L40S ($0.28)** — $0.074/1k steps — nearly tied with 3090 spot, 2.8x faster wall-clock
4. **RTX 4090* ($0.17)** — $0.097/1k steps — theoretical, needs measurement
5. **1xH100* ($1.29)** — $0.123/1k steps — theoretical
6. **8xH100 ($10.32)** — $0.123/1k steps — fastest wall-clock (10 min full run)
7. **RTX 3090 (on-demand $0.21)** — $0.153/1k steps — 3x worse than 5090

## Measured Step Times

| GPU | VRAM | Step avg (ms) | 500 steps | 13,780 steps | Source | Date |
|-----|------|--------------|-----------|-------------|--------|------|
| 8xH100 (8 GPUs) | 80GB×8 | ~43 | ~22s | 600s (10 min) | — | — |
| 1xRTX 5090 (Novita) | 32GB | ~605 | ~5 min | ~2.3 hrs | queue_gpu4.txt runs | 2026-03-21 |
| 1xLegacy L40S (Novita, torch.compile) | 48GB | ~950 | ~8 min | ~3.6 hrs | queue_gpu3.txt runs | 2026-03-21 |
| 1xLegacy L40S (old measurement) | 48GB | ~2,294-2,487 | ~19-21 min | ~8.8-9.5 hrs | monitor_status.log (multiple runs) | 2026-03-19 |
| 1xRTX 3090 (local) | 24GB | ~2,629 | ~22 min | ~10.1 hrs | local smoke + activation runs | 2026-03-21 |
| 1xRTX 3090 (remote, Novita) | 24GB | ~2,702 | ~23 min | ~10.3 hrs | remote activation runs | 2026-03-21 |

## Relative Speed (vs RTX 3090 baseline ~2,629ms)

| GPU | Relative speed | Notes |
|-----|---------------|-------|
| RTX 5090 | 4.35x faster | SM 12.0 (Blackwell), torch.compile, 1792 GB/s bandwidth |
| Legacy L40S (torch.compile) | 2.77x faster | SM 8.9 (Ada), torch.compile — MUCH faster than old L40S measurement |
| Legacy L40S (old, no compile?) | 1.06-1.15x faster | Old measurement, possibly without torch.compile or different driver |
| RTX 3090 (local) | 1.00x | SM 8.6, eager mode (no torch.compile) |
| RTX 3090 (remote) | 0.97x | Same GPU, slightly slower (thermal/clock) |

## Memory Usage

| GPU | Peak allocated | Peak reserved |
|-----|---------------|--------------|
| RTX 3090 (24GB) | 13,830 MiB | 14,150 MiB |

## Pricing & Cost-Efficiency Analysis

### Rental Prices (Novita AI)

All hourly prices below are Novita AI rental rates.

| GPU | $/hr |
|-----|------|
| RTX 3090 (spot) | $0.10 |
| RTX 4090 | $0.17 |
| RTX 3090 (on-demand) | $0.21 |
| Legacy L40S | $0.28 |
| RTX 5090 | $0.30 |
| 1xH100 | $1.29 |
| 8xH100 | $10.32 (8 × $1.29) |

### Cost Per Training Run

Step times marked with * are **theoretical estimates**. RTX 5090 and the legacy L40S are now **measured**.

| GPU | Step time (ms) | Hours for 13,780 steps | Cost (full run) | Cost (500 steps) | $/step |
|-----|---------------|----------------------|----------------|-----------------|--------|
| RTX 5090 | 605 | 2.32 hr | **$0.70** | $0.025 | $0.0000504 |
| RTX 3090 (spot) | 2,629 | 10.06 hr | **$1.01** | $0.037 | $0.0000730 |
| Legacy L40S | 950 | 3.64 hr | **$1.02** | $0.037 | $0.0000739 |
| RTX 4090 | ~2,057* | ~7.87 hr | **$1.34*** | $0.049* | $0.0000971* |
| 1xH100 | ~344* | ~1.32 hr | **$1.70*** | $0.062* | $0.0001232* |
| 8xH100 | 43 | 0.165 hr | **$1.70** | $0.062 | $0.0001232 |
| RTX 3090 (on-demand) | 2,629 | 10.06 hr | **$2.11** | $0.077 | $0.0001534 |

### Theoretical vs Measured Step Times

This model appears **memory-bandwidth-bound**, but torch.compile makes a huge difference.

**Measured (2026-03-21):**
- **RTX 5090**: 605 ms/step — **1.9x faster than theoretical** (predicted ~1,157ms). Blackwell SM 12.0 + torch.compile.
- **Legacy L40S**: 950 ms/step — **2.5x faster than old measurement** (~2,400ms). torch.compile likely the difference.
- **RTX 3090**: 2,629 ms/step — eager mode only (SM 8.6, no torch.compile)

**Still theoretical:**
- **RTX 4090**: ~2,057 ms/step (bandwidth-scaled, but likely much faster with torch.compile like the others)
- **1xH100**: ~344 ms/step (8× the 8xH100 step time)

**Key insight**: torch.compile delivers 2-4x speedup on this workload. The old legacy L40S measurement (~2,400ms) was likely without torch.compile or with an older driver. The RTX 5090 at 605ms is only ~1.8x slower than 8xH100 (43ms × 8 GPUs = 344ms effective single-GPU).

## FLOPS Comparison (RTX 5090 vs legacy L40S)

When training LLMs, BF16 and FP8 are the most relevant precisions. The legacy L40S leverages its enterprise architecture to achieve significantly higher theoretical compute, particularly when utilizing structural sparsity.

| GPU | Architecture | BF16 (Dense / Sparse) | FP8 (Dense / Sparse) | Notes |
|-----|-------------|-----------------------|----------------------|-------|
| **Legacy L40S** | Ada Lovelace (Enterprise) | 362 / 733 TFLOPS | 733 / 1,466 TFLOPS | Supports Transformer Engine (FP8/FP16 switching) |
| **RTX 5090** | Blackwell (Consumer) | ~209 TFLOPS (dense)* | ~419 TFLOPS (dense)* | *Tensor Cores w/ accumulate. No sparse acceleration. |

*Note: While the legacy L40S has substantially more raw compute (FLOPS), typical LLM training is often memory-bandwidth-bound. The RTX 5090 has more memory bandwidth (1,792 GB/s) compared to the L40S (864 GB/s), which may make the 5090 faster in practice despite lower theoretical FLOPS.*

## Notes

- The old legacy L40S measurement (~2,294-2,487ms) was likely without torch.compile or with older drivers. New legacy L40S measurement (950ms) is 2.5x faster.
- RTX 5090 measured 605ms — nearly 2x faster than the theoretical bandwidth-scaled estimate of 1,157ms. torch.compile + Blackwell architecture.
- 3090 has sufficient VRAM (uses ~14GB of 24GB available). 5090 uses ~11.5GB of 32GB.
- Per-step dynamics (loss curves, gradients) are identical across GPUs — only wall-clock differs.
- RTX 3090 runs in eager mode (torch.compile disabled, SM 8.6). Legacy L40S (SM 8.9) and RTX 5090 (SM 12.0) use torch.compile.
- All remote GPUs are Novita cloud instances (proxy.us-ca-6.gpu-instance.novita.ai).
- Active GPU fleet (as of 2026-03-21): 1x local 3090, 1x remote 3090 (:62248), 1x RTX 5090 (:62132).
