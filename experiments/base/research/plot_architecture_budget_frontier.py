from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


RESULTS_DIR = Path("results")
OUT_PATH = Path("research/figures/architecture_budget_frontier.png")
SIZE_LIMIT_MB = 16.0
SIZE_LIMIT_BYTES = 16_000_000


def classify_run(run_id: str) -> str:
    if "_moe" in run_id or run_id.startswith("arch_moe") or "moe" in run_id:
        return "MoE"
    if "embed_" in run_id:
        return "Factored embed"
    if "conv_" in run_id:
        return "Depthwise conv"
    if "_ws_" in run_id or run_id.startswith("arch_ws"):
        return "Weight sharing"
    if "qat" in run_id:
        return "QAT"
    return "Other"


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(RESULTS_DIR.glob("arch*/summary.json")):
        with path.open() as f:
            data = json.load(f)
        last_eval = data.get("last_eval") or {}
        final_quant = data.get("final_quant_eval") or {}
        total_bytes = data.get("int8_zlib_total_submission_bytes")
        if last_eval.get("max_steps") != 500:
            continue
        if total_bytes is None or final_quant.get("val_bpb") is None:
            continue
        run_id = data["run_id"]
        rows.append(
            {
                "run_id": run_id,
                "category": classify_run(run_id),
                "val_bpb": float(final_quant["val_bpb"]),
                "size_mb": total_bytes / 1_000_000,
                "legal": total_bytes <= SIZE_LIMIT_BYTES,
            }
        )
    return rows


def frontier(rows: list[dict], legal_only: bool) -> list[dict]:
    candidates = [row for row in rows if row["legal"] or not legal_only]
    candidates = sorted(candidates, key=lambda row: (row["size_mb"], row["val_bpb"]))
    best_so_far = np.inf
    points: list[dict] = []
    for row in candidates:
        if row["val_bpb"] < best_so_far - 1e-9:
            points.append(row)
            best_so_far = row["val_bpb"]
    return points


def make_plot(rows: list[dict]) -> None:
    plt.style.use("default")
    fig = plt.figure(figsize=(14, 7.5), facecolor="#f6f2e8")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.65, 1.0], wspace=0.18)
    ax = fig.add_subplot(gs[0, 0], facecolor="#fffdf8")
    bar_ax = fig.add_subplot(gs[0, 1], facecolor="#fffdf8")

    colors = {
        "MoE": "#c44e52",
        "Factored embed": "#4c78a8",
        "Depthwise conv": "#9c755f",
        "Weight sharing": "#59a14f",
        "QAT": "#b279a2",
        "Other": "#7f7f7f",
    }

    for category, color in colors.items():
        pts = [row for row in rows if row["category"] == category]
        if not pts:
            continue
        legal = [row for row in pts if row["legal"]]
        illegal = [row for row in pts if not row["legal"]]
        if legal:
            ax.scatter(
                [row["size_mb"] for row in legal],
                [row["val_bpb"] for row in legal],
                s=54,
                c=color,
                alpha=0.9,
                label=category,
                edgecolors="white",
                linewidths=0.6,
            )
        if illegal:
            ax.scatter(
                [row["size_mb"] for row in illegal],
                [row["val_bpb"] for row in illegal],
                s=54,
                facecolors="none",
                edgecolors=color,
                alpha=0.8,
                linewidths=1.4,
            )

    legal_frontier = frontier(rows, legal_only=True)
    all_frontier = frontier(rows, legal_only=False)
    ax.plot(
        [row["size_mb"] for row in all_frontier],
        [row["val_bpb"] for row in all_frontier],
        color="#c44e52",
        linewidth=2.2,
        alpha=0.7,
    )
    ax.plot(
        [row["size_mb"] for row in legal_frontier],
        [row["val_bpb"] for row in legal_frontier],
        color="#1f1f1f",
        linewidth=2.6,
    )

    ax.axvline(SIZE_LIMIT_MB, color="#1f1f1f", linestyle="--", linewidth=1.4, alpha=0.85)
    ax.text(SIZE_LIMIT_MB + 0.08, 1.59, "16 MB submission cap", fontsize=11, color="#1f1f1f")

    labels = {
        "arch_moe_4e_leaky": (-0.85, -0.010),
        "arch_embed_bn128_untied": (0.10, -0.010),
        "arch_embed_baseline": (0.10, 0.008),
        "arch_moe_2e_10L": (0.10, 0.006),
        "arch_conv_baseline": (0.10, 0.008),
    }
    by_id = {row["run_id"]: row for row in rows}
    for run_id, (dx, dy) in labels.items():
        row = by_id.get(run_id)
        if row is None:
            continue
        ax.scatter(
            [row["size_mb"]],
            [row["val_bpb"]],
            s=86,
            c=colors.get(row["category"], "#7f7f7f"),
            edgecolors="#1f1f1f",
            linewidths=1.0,
            zorder=5,
        )
        ax.annotate(
            run_id.replace("arch_", ""),
            (row["size_mb"], row["val_bpb"]),
            xytext=(row["size_mb"] + dx, row["val_bpb"] + dy),
            textcoords="data",
            fontsize=10.5,
            color="#1f1f1f",
            arrowprops={"arrowstyle": "-", "color": "#555555", "lw": 0.8},
        )

    ax.set_title("500-step architecture sweep: size budget changes the winner", fontsize=15, color="#1f1f1f", pad=12)
    ax.set_xlabel("Compressed submission size (MB)")
    ax.set_ylabel("Post-quant val_bpb on FineWeb\nlower is better")
    ax.set_xlim(4.0, 21.2)
    ax.set_ylim(1.59, 1.425)
    ax.grid(alpha=0.18, color="#6e6259")
    leg = ax.legend(loc="lower left", frameon=True, fontsize=10)
    leg.get_frame().set_facecolor("#fffdf8")
    leg.get_frame().set_edgecolor("#cabfae")

    best_by_category = []
    for category in colors:
        pts = [row for row in rows if row["category"] == category]
        if not pts:
            continue
        best = min(pts, key=lambda row: row["val_bpb"])
        best_by_category.append(best)
    best_by_category.sort(key=lambda row: row["val_bpb"])

    y = np.arange(len(best_by_category))
    bar_vals = [row["val_bpb"] for row in best_by_category]
    bar_labels = [
        f"{row['category']}  {'legal' if row['legal'] else 'over cap'}"
        for row in best_by_category
    ]
    bar_colors = [colors[row["category"]] for row in best_by_category]
    bar_ax.barh(y, bar_vals, color=bar_colors, alpha=0.92)
    bar_ax.set_yticks(y, bar_labels)
    bar_ax.invert_yaxis()
    bar_ax.set_xlim(1.59, 1.425)
    bar_ax.set_title("Best run per family", fontsize=15, color="#1f1f1f", pad=12)
    bar_ax.grid(axis="x", alpha=0.18, color="#6e6259")
    for idx, row in enumerate(best_by_category):
        marker = "legal" if row["legal"] else "over cap"
        bar_ax.text(
            row["val_bpb"] + 0.0015,
            idx,
            f"{row['val_bpb']:.4f}   {row['size_mb']:.1f} MB   {marker}",
            va="center",
            fontsize=10,
            color="#1f1f1f",
        )

    fig.suptitle(
        "Parameter Golf takeaway: raw accuracy loves MoE, but the 16 MB artifact limit rewards efficient dense changes",
        fontsize=18,
        color="#1f1f1f",
        y=0.98,
    )
    fig.text(
        0.055,
        0.03,
        "Source: 82 architecture summaries under results/arch*/summary.json, filtered to runs with last_eval.max_steps == 500.",
        fontsize=10.5,
        color="#4e473f",
    )
    fig.text(
        0.055,
        0.01,
        "Filled markers fit the 16 MB limit. Hollow markers beat them on BPB but are not currently legal submissions.",
        fontsize=10.5,
        color="#4e473f",
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit("No 500-step architecture summaries found.")
    make_plot(rows)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
