"""High-level LLM facade: model routing, usage/cost logging, embeddings."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings

from .pricing import estimate_cost
from .provider import LLMNotConfigured, LLMResult, NvidiaNIMProvider

logger = logging.getLogger(__name__)

_provider: NvidiaNIMProvider | None = None


def is_configured() -> bool:
    return bool(getattr(settings, "NVIDIA_API_KEY", ""))


def get_provider() -> NvidiaNIMProvider:
    global _provider
    if _provider is None:
        if not is_configured():
            raise LLMNotConfigured("NVIDIA_API_KEY is not set; LLM features are disabled")
        _provider = NvidiaNIMProvider(
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    return _provider


def model_for_role(role: str) -> str:
    """Route to a cheap model for routine extraction, a stronger one for assessment."""
    return {
        "extract": settings.LLM_MODEL_EXTRACT,
        "assess": settings.LLM_MODEL_ASSESS,
    }.get(role, settings.LLM_MODEL_EXTRACT)


def log_usage(operation: str, result: LLMResult, *, target=None):
    """Persist token + estimated-cost accounting for one call."""
    from .models import LLMUsage

    cost = estimate_cost(result.model, result.usage.prompt_tokens, result.usage.completion_tokens)
    total = result.usage.total_tokens or (
        result.usage.prompt_tokens + result.usage.completion_tokens
    )
    usage = LLMUsage.objects.create(
        operation=operation,
        model=result.model,
        prompt_tokens=result.usage.prompt_tokens,
        completion_tokens=result.usage.completion_tokens,
        total_tokens=total,
        cost_usd=Decimal(str(round(cost, 6))),
        target=target,
    )
    logger.info(
        "llm op=%s model=%s tokens=%s/%s cost=$%.6f",
        operation,
        result.model,
        result.usage.prompt_tokens,
        result.usage.completion_tokens,
        cost,
    )
    return usage


def chat(
    messages: list[dict],
    *,
    role: str = "extract",
    max_tokens: int | None = None,
    temperature: float | None = None,
    operation: str | None = None,
    target=None,
) -> LLMResult:
    """Send a chat completion, routed by role, with usage logged."""
    provider = get_provider()
    result = provider.chat(
        messages,
        model=model_for_role(role),
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
    )
    try:
        log_usage(operation or role, result, target=target)
    except Exception:
        logger.exception("LLM usage logging failed")
    return result


def embed(texts: list[str], *, input_type: str = "passage") -> list[list[float]]:
    """Return embedding vectors for the given texts (used by the semantic-diff layer)."""
    return get_provider().embed(texts, model=settings.LLM_EMBED_MODEL, input_type=input_type)
