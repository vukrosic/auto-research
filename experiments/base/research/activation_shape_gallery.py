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


def gate_linear(x: np.ndarray) -> np.ndarray:
    return x


def gate_mild(x: np.ndarray, floor: float = 0.5) -> np.ndarray:
    return floor + (1.0 - floor) * sigmoid(x)


def gate_silu(x: np.ndarray) -> np.ndarray:
    return silu(x)


def power_relu(x: np.ndarray, p: float) -> np.ndarray:
    return np.power(relu(x), p)


def plot_family_curves(out_dir: Path) -> None:
    x = np.linspace(-4.0, 4.0, 1200)

    final_curves = {
        "relu2": power_relu(x, 2.0),
        "relu1.8": power_relu(x, 1.8),
        "relu2.2": power_relu(x, 2.2),
        "gated_relu2": power_relu(x, 2.0) * sigmoid(x),
        "mild_gated_relu2": power_relu(x, 2.0) * gate_mild(x, floor=0.5),
        "mild_gated_relu22": power_relu(x, 2.2) * gate_mild(x, floor=0.5),
        "reluglu": relu(x) * gate_linear(x),
        "swirelu": relu(x) * gate_silu(x),
        "swiglu": silu(x) * gate_linear(x),
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    for name, y in final_curves.items():
        ax.plot(x, y, linewidth=2, label=name)
    ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.5)
    ax.axvline(0.0, color="black", linewidth=0.8, alpha=0.5)
    ax.set_title("Activation Output Shapes")
    ax.set_xlabel("scalar input")
    ax.set_ylabel("output shape")
    ax.set_xlim(-4.0, 4.0)
    ax.set_ylim(-1.0, 18.0)
    ax.legend(ncol=3, fontsize=9)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "activation_output_shapes.png", dpi=180)
    plt.close(fig)

    gate_curves = {
        "sigmoid": sigmoid(x),
        "mild gate floor=0.5": gate_mild(x, floor=0.5),
        "mild gate floor=0.7": gate_mild(x, floor=0.7),
        "silu gate": gate_silu(x),
        "linear gate": gate_linear(x),
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    for name, y in gate_curves.items():
        ax.plot(x, y, linewidth=2, label=name)
    ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.5)
    ax.axvline(0.0, color="black", linewidth=0.8, alpha=0.5)
    ax.set_title("Gate Shapes")
    ax.set_xlabel("scalar input")
    ax.set_ylabel("gate value")
    ax.set_xlim(-4.0, 4.0)
    ax.set_ylim(-4.0, 4.0)
    ax.legend(ncol=2, fontsize=9)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "activation_gate_shapes.png", dpi=180)
    plt.close(fig)

    families = {
        "power relu": [("p=1.8", power_relu(x, 1.8)), ("p=2.0", power_relu(x, 2.0)), ("p=2.2", power_relu(x, 2.2)), ("p=2.4", power_relu(x, 2.4))],
        "mild gated power relu": [
            ("p=1.8 f=0.5", power_relu(x, 1.8) * gate_mild(x, 0.5)),
            ("p=2.0 f=0.5", power_relu(x, 2.0) * gate_mild(x, 0.5)),
            ("p=2.3 f=0.5", power_relu(x, 2.3) * gate_mild(x, 0.5)),
            ("p=2.3 f=0.7", power_relu(x, 2.3) * gate_mild(x, 0.7)),
        ],
    }
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    for ax, (title, curves) in zip(axes, families.items()):
        for name, y in curves:
            ax.plot(x, y, linewidth=2, label=name)
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.5)
        ax.axvline(0.0, color="black", linewidth=0.8, alpha=0.5)
        ax.set_title(title)
        ax.set_xlabel("scalar input")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("output shape")
    axes[0].set_ylim(-1.0, 18.0)
    fig.tight_layout()
    fig.savefig(out_dir / "activation_frankenstein_family.png", dpi=180)
    plt.close(fig)


def write_readme(out_dir: Path) -> None:
    text = """# Activation Shape Gallery

Read these first:

- `activation_output_shapes.png`: direct comparison of the most interesting discovered shapes
- `activation_frankenstein_family.png`: the parametric family we are now testing

Skip if you want:

- `activation_gate_shapes.png`: just the gate terms by themselves

What to look for:

- good candidates stay exactly zero on the negative side
- good candidates grow faster than linear on the positive side
- good gates mostly rescale the positive branch instead of inventing a whole new smooth path
"""
    (out_dir / "README.md").write_text(text)


def main() -> None:
    out_dir = Path("lab/activation_plots")
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_family_curves(out_dir)
    write_readme(out_dir)
    print(out_dir.resolve())


if __name__ == "__main__":
    main()
