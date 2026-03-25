# Live State

This directory holds derived operational views of the lab's current state.

## Authority Rule

These files are **not** the source of truth. They are human-readable dashboards derived from primary records:

- Experiment status lives in `experiments/<project>/snapshots/*/status`
- Experiment metadata lives in `experiments/<project>/snapshots/*/meta.json`
- Frontier records live in `experiments/<project>/current_best.json`

If a state file disagrees with the primary records, the primary records win. Regenerate the state files.

## Reconciliation

At session open, reconcile these files against primary records before using them for decisions. See [07_CADENCE.md](/root/research/autoresearch/lab/07_CADENCE.md) for the reconciliation rule.

## Files

- [Frontier](/root/research/autoresearch/state/FRONTIER.md) — derived from `experiments/<project>/current_best.json`
- [Active Runs](/root/research/autoresearch/state/ACTIVE_RUNS.md) — derived from snapshot status files
- [Adjudication Queue](/root/research/autoresearch/state/ADJUDICATION_QUEUE.md) — derived from snapshots with `status=done`
- [Open Questions](/root/research/autoresearch/state/OPEN_QUESTIONS.md) — maintained manually, reviewed per cadence
