# Local-Only Snapshot Data

This directory exists for live experiment snapshots on the operator's machine.

It is intentionally excluded from the public repository so GitHub clones do not pull large volumes of experiment state and result files.

Typical local contents include:

- experiment metadata
- status files
- preflight records
- parsed results
- temporary runtime artifacts

If you are cloning the public repo, this directory will stay mostly empty until you run your own experiments locally.
