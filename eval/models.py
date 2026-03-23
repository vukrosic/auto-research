"""LLM provider registry — unified interface for benchmarking different models.

Add a new model: just add an entry to MODELS dict and set the API key env var.
All OpenAI-compatible providers share the same client code.
"""
import os
import time
from dataclasses import dataclass, field
from openai import OpenAI


@dataclass
class LLMResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    error: str = ""


# ── Model Registry ────────────────────────────────────────────────────────

MODELS = {
    # Current production model — the only one we benchmark for now.
    # To add another: copy this block, change the key and fields, set the API key env var.
    "mimo-v2-flash": {
        "provider": "openai_compat",
        "base_url": "https://api.novita.ai/openai",
        "model": "xiaomimimo/mimo-v2-flash",
        "api_key_env": "NOVITA_API_KEY",
        "price_input": 0.10,   # per 1M tokens
        "price_output": 0.30,
    },
}

# ── Client cache ──────────────────────────────────────────────────────────
_clients: dict[str, object] = {}


def _get_openai_client(model_id: str) -> OpenAI:
    if model_id not in _clients:
        cfg = MODELS[model_id]
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            raise ValueError(f"Set {cfg['api_key_env']} env var for {model_id}")
        kwargs = {"api_key": api_key, "base_url": cfg["base_url"]}
        if cfg.get("extra_headers"):
            kwargs["default_headers"] = cfg["extra_headers"]
        _clients[model_id] = OpenAI(**kwargs)
    return _clients[model_id]


def _get_anthropic_client(model_id: str):
    if model_id not in _clients:
        cfg = MODELS[model_id]
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            raise ValueError(f"Set {cfg['api_key_env']} env var for {model_id}")
        import anthropic
        _clients[model_id] = anthropic.Anthropic(api_key=api_key)
    return _clients[model_id]


def _calc_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    cfg = MODELS[model_id]
    return (
        input_tokens * cfg["price_input"] / 1_000_000
        + output_tokens * cfg["price_output"] / 1_000_000
    )


# ── Unified call interface ────────────────────────────────────────────────

def call_llm(model_id: str, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
    """Call any registered LLM with a unified interface.

    Args:
        model_id: Key from MODELS dict
        messages: OpenAI-format messages [{"role": "system"|"user"|"assistant", "content": "..."}]
        temperature: Sampling temperature
        max_tokens: Max output tokens

    Returns:
        LLMResponse with content, tokens, latency, cost
    """
    cfg = MODELS.get(model_id)
    if not cfg:
        return LLMResponse(content="", error=f"Unknown model: {model_id}. Available: {list(MODELS.keys())}")

    try:
        if cfg["provider"] == "anthropic":
            return _call_anthropic(model_id, cfg, messages, temperature, max_tokens)
        else:
            return _call_openai_compat(model_id, cfg, messages, temperature, max_tokens)
    except Exception as e:
        return LLMResponse(content="", error=str(e))


def _call_openai_compat(model_id: str, cfg: dict, messages: list[dict],
                         temperature: float, max_tokens: int) -> LLMResponse:
    client = _get_openai_client(model_id)
    t0 = time.time()
    response = client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.choices[0].message.content or ""
    usage = response.usage
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0

    return LLMResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        cost_usd=_calc_cost(model_id, input_tokens, output_tokens),
    )


def _call_anthropic(model_id: str, cfg: dict, messages: list[dict],
                     temperature: float, max_tokens: int) -> LLMResponse:
    client = _get_anthropic_client(model_id)

    # Extract system message
    system = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system = msg["content"]
        else:
            chat_messages.append(msg)

    t0 = time.time()
    response = client.messages.create(
        model=cfg["model"],
        system=system,
        messages=chat_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.content[0].text if response.content else ""
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    return LLMResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        cost_usd=_calc_cost(model_id, input_tokens, output_tokens),
    )


def list_available_models() -> list[str]:
    """Return model IDs that have their API key set."""
    available = []
    for model_id, cfg in MODELS.items():
        if os.environ.get(cfg["api_key_env"]):
            available.append(model_id)
    return available
