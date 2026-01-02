"""Token cost estimation.

These are representative USD rates per 1M tokens (prompt, completion). The
cost-savings metric is *relative* (cheap vs strong model, skip-unchanged), so
consistency matters more than absolute precision. Override via the LLM_PRICING
setting if desired.
"""

from __future__ import annotations

from django.conf import settings

# USD per 1,000,000 tokens: {model: (prompt_rate, completion_rate)}
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    "meta/llama-3.1-8b-instruct": (0.05, 0.05),
    "meta/llama-3.3-70b-instruct": (0.30, 0.30),
    "nvidia/nv-embedqa-e5-v5": (0.02, 0.0),
}
FALLBACK_RATE: tuple[float, float] = (0.20, 0.20)


def _rates(model: str) -> tuple[float, float]:
    table = {**DEFAULT_PRICING, **getattr(settings, "LLM_PRICING", {})}
    return table.get(model, FALLBACK_RATE)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_rate, completion_rate = _rates(model)
    return (prompt_tokens / 1_000_000) * prompt_rate + (
        completion_tokens / 1_000_000
    ) * completion_rate
