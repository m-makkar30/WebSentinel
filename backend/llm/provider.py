"""Provider interface + the NVIDIA NIM implementation.

NVIDIA's hosted API is OpenAI-compatible, so we use the standard `openai`
client pointed at NVIDIA's base URL. Keeping a thin interface here means model
routing and the provider stay swappable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class LLMNotConfigured(RuntimeError):
    """Raised when the LLM provider is used without an API key configured."""


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResult:
    text: str
    model: str
    usage: Usage = field(default_factory=Usage)


class LLMProvider(Protocol):
    def chat(
        self, messages: list[dict], *, model: str, max_tokens: int, temperature: float
    ) -> LLMResult: ...

    def embed(self, texts: list[str], *, model: str, input_type: str) -> list[list[float]]: ...


class NvidiaNIMProvider:
    """OpenAI-compatible client targeting NVIDIA NIM."""

    def __init__(self, *, api_key: str, base_url: str, timeout: float, max_retries: int) -> None:
        from openai import OpenAI

        # The OpenAI client retries 429/5xx with exponential backoff and honors
        # the request timeout — that covers the retry/timeout requirement.
        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries
        )

    def chat(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int,
        temperature: float = 0.2,
    ) -> LLMResult:
        # max_tokens MUST be set explicitly or NVIDIA's endpoint errors.
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        u = response.usage
        usage = Usage(
            prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(u, "completion_tokens", 0) or 0,
            total_tokens=getattr(u, "total_tokens", 0) or 0,
        )
        text = response.choices[0].message.content or ""
        return LLMResult(text=text, model=getattr(response, "model", model) or model, usage=usage)

    def embed(
        self, texts: list[str], *, model: str, input_type: str = "passage"
    ) -> list[list[float]]:
        # NVIDIA embedding models require input_type (query|passage) and truncate.
        response = self._client.embeddings.create(
            model=model,
            input=texts,
            extra_body={"input_type": input_type, "truncate": "END"},
        )
        return [item.embedding for item in response.data]
