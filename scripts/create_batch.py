#!/usr/bin/env python3
"""Create a batch of explore experiments from a definition list.
Usage: python3 create_batch.py <batch_file.json>

batch_file.json format:
[
  {"name": "explore_foo", "env": {"KEY": "VAL"}, "hypothesis": "...", "dur": 720},
  ...
]

All experiments get SKIP_QUANT_EVAL=1 and VAL_LOSS_EVERY=500 automatically.
"""
import json, os, shutil, datetime, sys

AUTORESEARCH = "/root/research/autoresearch"
PROJECT = "parameter-golf"
SNAPSHOTS = f"{AUTORESEARCH}/experiments/{PROJECT}/snapshots"
BASE_DIR = f"{AUTORESEARCH}/experiments/{PROJECT}/base"

with open(f"{AUTORESEARCH}/experiments/{PROJECT}/base_id.txt") as f:
    PARENT_BASE = f.read().strip()

with open(f"{AUTORESEARCH}/experiments/{PROJECT}/current_best.json") as f:
    best = json.load(f)
sb = best.get("stage_baselines", {}).get("explore", {})
baseline_metric = sb.get("val_bpb", 1.6673)

batch = json.load(open(sys.argv[1]))
created, skipped = 0, 0

for exp in batch:
    name = exp["name"]
    snap_dir = f"{SNAPSHOTS}/{name}"
    if os.path.exists(snap_dir):
        print(f"SKIP (exists): {name}")
        skipped += 1
        continue

    os.makedirs(snap_dir)
    shutil.copytree(BASE_DIR, f"{snap_dir}/code")

    env = {"SKIP_QUANT_EVAL": "1", "VAL_LOSS_EVERY": "500"}
    env.update(exp.get("env", {}))

    meta = {
        "name": name, "project": PROJECT,
        "hypothesis": exp.get("hypothesis", ""),
        "parent_base": PARENT_BASE, "stage": "explore",
        "steps": 500, "priority": exp.get("priority", 1),
        "created_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "gpu": None, "baseline_metric": baseline_metric,
        "promotion_threshold": 0.01, "env_overrides": env,
        "changes_summary": "", "owner": "autonomous_lab",
        "expected_duration_seconds": exp.get("dur", 720),
    }
    with open(f"{snap_dir}/meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    with open(f"{snap_dir}/status", "w") as f:
        f.write("pending")
    print(f"CREATED: {name}")
    created += 1

print(f"\n=== {created} created, {skipped} skipped ===")
