#!/usr/bin/env python3
"""Parse a training log and plot loss curves."""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

log_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else log_path.rsplit(".", 1)[0] + ".png"

with open(log_path) as f:
    log = f.read()

train_steps, train_losses, train_times = [], [], []
val_steps, val_losses, val_bpbs, val_times = [], [], [], []

for line in log.splitlines():
    m = re.search(r"step:(\d+)/\d+\s+train_loss:([\d.]+)\s+train_time:([\d.]+)ms", line)
    if m:
        train_steps.append(int(m.group(1)))
        train_losses.append(float(m.group(2)))
        train_times.append(float(m.group(3)) / 1000)
        continue
    m = re.search(r"step:(\d+)/\d+\s+val_loss:([\d.]+)\s+val_bpb:([\d.]+)\s+train_time:([\d.]+)ms", line)
    if m:
        val_steps.append(int(m.group(1)))
        val_losses.append(float(m.group(2)))
        val_bpbs.append(float(m.group(3)))
        val_times.append(float(m.group(4)) / 1000)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

ax = axes[0]
if train_steps:
    ax.plot(train_steps, train_losses, "b.-", alpha=0.7, label="train loss")
if val_steps:
    ax.plot(val_steps, val_losses, "ro-", markersize=6, label="val loss")
ax.set_xlabel("Step")
ax.set_ylabel("Loss")
ax.set_title("Loss vs Step")
ax.legend()
ax.grid(True, alpha=0.3)

ax = axes[1]
if train_steps:
    ax.plot(train_times, train_losses, "b.-", alpha=0.7, label="train loss")
if val_steps:
    ax.plot(val_times, val_losses, "ro-", markersize=6, label="val loss")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Loss")
ax.set_title("Loss vs Wall-clock Time")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(out_path, dpi=100)
print(f"Saved plot to {out_path}")
