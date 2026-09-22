"""httpx-based chat-completion providers for the LLM judge.

Credentials come only from environment variables (``OPENAI_API_KEY``,
``OPENAI_BASE_URL``, ``ANTHROPIC_API_KEY``) -- never hard-coded, never logged, never
included in an exception message.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx

__all__ = [
    "AnthropicProvider",
    "JudgeProvider",
    "OpenAICompatProvider",
    "ProviderResponse",
    "estimate_cost_usd",
    "provider_for_name",
]


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    text: str
    input_tokens: int
    output_tokens: int


class JudgeProvider(Protocol):
    model: str

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse: ...


class OpenAICompatProvider:
    """OpenAI Chat Completions API, or any provider exposing the same wire shape."""

    def __init__(self, model: str, *, timeout: float = 60.0) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.model = model
        self._api_key = api_key
        self._base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse:
        response = client.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        return ProviderResponse(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
        )


class AnthropicProvider:
    """Anthropic Messages API."""

    def __init__(self, model: str, *, timeout: float = 60.0, max_tokens: int = 1024) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.model = model
        self._api_key = api_key
        self._timeout = timeout
        self._max_tokens = max_tokens

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        text = "".join(block.get("text", "") for block in body.get("content", []))
        usage = body.get("usage") or {}
        return ProviderResponse(
            text=text,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )


def provider_for_name(name: str, model: str) -> JudgeProvider:
    if name == "openai_compat":
        return OpenAICompatProvider(model)
    if name == "anthropic":
        return AnthropicProvider(model)
    raise ValueError(f"unknown provider {name!r}, expected openai_compat|anthropic")


_PRICING_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4o": (2.5, 10.0),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4.1": (2.0, 8.0),
    "claude-3-5-haiku": (0.8, 4.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-opus": (15.0, 75.0),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Approximate USD cost for one completion, or ``None`` if ``model`` has no known price."""
    for prefix, (in_price, out_price) in _PRICING_PER_1M_TOKENS.items():
        if model.startswith(prefix):
            return input_tokens / 1_000_000 * in_price + output_tokens / 1_000_000 * out_price
    return None
