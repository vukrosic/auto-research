"""Research template registry.

Each template is a pointer to a research repo with:
- A training script
- An experiment runner
- A results directory
- Allowed config overrides
"""
from pathlib import Path
from dataclasses import dataclass

from api.config import settings


@dataclass
class ResearchTemplate:
    name: str
    path: str  # Path to the research repo
    train_script: str  # Relative path to training script
    runner_script: str  # Relative path to experiment runner
    results_dir: str  # Relative path to results directory
    allowed_overrides: list[str]  # Env vars users can set
    metric: str  # Primary metric (e.g., val_bpb)
    metric_direction: str  # "lower" or "higher" is better


# Parameter Golf — the first template
PARAMETER_GOLF = ResearchTemplate(
    name="parameter_golf",
    path=settings.parameter_golf_path,
    train_script="train_gpt.py",
    runner_script="infra/run_experiment.sh",
    results_dir="results",
    allowed_overrides=[
        "MATRIX_LR", "SCALAR_LR", "EMBED_LR",
        "NUM_LAYERS", "MODEL_DIM", "NUM_HEADS", "NUM_KV_HEADS",
        "MLP_MULT", "WARMDOWN_ITERS", "WARMUP_STEPS",
        "LOGIT_SOFTCAP", "QK_GAIN_INIT", "ROPE_BASE",
        "MUON_MOMENTUM", "GRAD_CLIP_NORM",
        "TIED_EMBED_LR", "TIED_EMBED_INIT_STD",
    ],
    metric="val_bpb",
    metric_direction="lower",
)

# Template registry
TEMPLATES: dict[str, ResearchTemplate] = {
    "parameter_golf": PARAMETER_GOLF,
}


def get_template(name: str) -> ResearchTemplate:
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[name]


def validate_overrides(template_name: str, overrides: dict) -> list[str]:
    """Return list of invalid override keys."""
    template = get_template(template_name)
    return [k for k in overrides if k not in template.allowed_overrides]
