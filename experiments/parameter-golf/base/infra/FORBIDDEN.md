# Forbidden

Learning rate tuning is forbidden.

This research lane must focus on:

- new architectures
- mechanism changes
- scientific contribution
- experimentally defensible model design ideas

Do not treat optimizer LR sweeps as scientific progress.

Leaving GPUs idle while queued experiments exist is forbidden.

- If any GPU is free and there is a queued experiment, start the next experiment immediately.
- Do not wait for all current runs to finish before launching the next queued run.
