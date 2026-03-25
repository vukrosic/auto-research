from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def silu(x: np.ndarray) -> np.ndarray:
    return x / (1.0 + np.exp(-x))


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def power_relu(x: np.ndarray, p: float) -> np.ndarray:
    return np.power(relu(x), p)


def main() -> None:
    out_dir = Path("lab/activation_plots")
    out_dir.mkdir(parents=True, exist_ok=True)

    x = np.linspace(-4.0, 4.0, 1200)

    curves = [
        ("relu", relu(x), {"color": "#8c8c8c", "lw": 2.5, "ls": "--"}),
        ("relu²", power_relu(x, 2.0), {"color": "#2f6bff", "lw": 3.5}),
        ("silu²", np.power(silu(x), 2.0), {"color": "#f28e2b", "lw": 3.0}),
        ("gated relu²", power_relu(x, 2.0) * sigmoid(x), {"color": "#b07aa1", "lw": 3.0}),
    ]

    bpb_rows = [
        ("relu²", 1.4522),
        ("silu²", 1.4841),
        ("gated relu²", 1.4796),
        ("relu", 1.5007),
        ("relu^1", 1.4778),
        ("relu^3", 1.5097),
    ]

    fig = plt.figure(figsize=(14, 7.875), facecolor="#0f1117")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1.0], height_ratios=[0.48, 1.0], wspace=0.18, hspace=0.12)

    title_ax = fig.add_subplot(gs[0, :])
    title_ax.set_facecolor("#0f1117")
    title_ax.axis("off")
    title_ax.text(
        0.0,
        0.82,
        "The useful takeaway",
        fontsize=22,
        fontweight="bold",
        color="white",
        va="top",
    )
    title_ax.text(
        0.0,
        0.28,
        "Hard zeros only help when they are paired with squaring. Gates hurt.",
        fontsize=15,
        color="#d0d4dc",
        va="top",
    )
    curve_ax = fig.add_subplot(gs[1, 0])
    bar_ax = fig.add_subplot(gs[1, 1])
    for ax in (curve_ax, bar_ax):
        ax.set_facecolor("#121622")

    for label, y, style in curves:
        curve_ax.plot(x, y, label=label, **style)

    curve_ax.axhline(0.0, color="#566070", lw=1.0, alpha=0.8)
    curve_ax.axvline(0.0, color="#566070", lw=1.0, alpha=0.8)
    curve_ax.set_xlim(-4.0, 4.0)
    curve_ax.set_ylim(-0.4, 18.0)
    curve_ax.set_title("Output shape", color="white", fontsize=15, pad=10)
    curve_ax.set_xlabel("input", color="#cfd5df")
    curve_ax.set_ylabel("activation", color="#cfd5df")
    curve_ax.tick_params(colors="#cfd5df")
    for spine in curve_ax.spines.values():
        spine.set_color("#404858")
    curve_ax.grid(alpha=0.12, color="white")
    leg = curve_ax.legend(frameon=True, facecolor="#0f1117", edgecolor="#404858", fontsize=11, loc="upper left")
    for text in leg.get_texts():
        text.set_color("white")

    names = [n for n, _ in bpb_rows]
    vals = [v for _, v in bpb_rows]
    colors = ["#2f6bff", "#f28e2b", "#b07aa1", "#8c8c8c", "#59a14f", "#e15759"]
    bars = bar_ax.barh(names, vals, color=colors, alpha=0.95)
    bar_ax.invert_yaxis()
    bar_ax.set_title("Lower BPB is better", color="white", fontsize=15, pad=10)
    bar_ax.set_xlabel("BPB", color="#cfd5df")
    bar_ax.tick_params(colors="#cfd5df")
    for spine in bar_ax.spines.values():
        spine.set_color("#404858")
    bar_ax.grid(axis="x", alpha=0.12, color="white")
    bar_ax.set_xlim(1.43, 1.52)
    for bar, val in zip(bars, vals):
        bar_ax.text(val + 0.001, bar.get_y() + bar.get_height() / 2, f"{val:.4f}", va="center", ha="left", color="white", fontsize=10)

    fig.text(0.02, 0.02, "Best result: relu² at 1.4522 BPB. Gates lost in every tested variant.", color="#7f8a9c", fontsize=11)
    fig.savefig(out_dir / "activation_x_takeaway.png", dpi=220, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(out_dir / "activation_x_takeaway.png")


if __name__ == "__main__":
    main()
