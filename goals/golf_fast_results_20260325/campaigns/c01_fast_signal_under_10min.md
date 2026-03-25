# Campaign c01 — Fast Signal Under 10 Minutes

**Status**: active
**Created**: 2026-03-25T13:04:13Z
**Project**: parameter-golf

## Goal

Use a fast non-quant 500-step screen to rank a small set of architecture candidates before spending more 45-minute explore runs.

## Queue

The canonical dispatch order is [`queue.json`](/root/research/autoresearch/goals/golf_fast_results_20260325/queue.json).

## Hypotheses

1. A fast non-quant proxy is sufficient to rank the next batch of architecture candidates.
2. At least one of the queued expert/depth variants will beat the fast baseline by more than noise.
3. The current long-tail explore path can be replaced with a no-quant screening lane for early triage.

## Decision Rule

- Keep only candidates that beat the fast baseline on `val_bpb`.
- If none beat baseline, stop the sprint and report that the current queued batch is weak under fast screening.
- If one clear winner appears, recommend promoting that axis to the regular explore/validate lane.
