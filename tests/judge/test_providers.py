from __future__ import annotations

from typing import Any

import httpx
import pytest

from forecheck.judge.providers import AnthropicProvider, OpenAICompatProvider, estimate_cost_usd


class _FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


def test_openai_compat_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAICompatProvider("gpt-4o-mini")


def test_openai_compat_provider_posts_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    captured: dict[str, Any] = {}

    def fake_post(
        self: httpx.Client, url: str, *, headers: Any = None, json: Any = None, timeout: Any = None
    ) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(
            {
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = OpenAICompatProvider("gpt-4o-mini")
    with httpx.Client() as client:
        response = provider.complete(system="sys", user="usr", client=client)

    assert response.text == "hello"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "gpt-4o-mini"


def test_anthropic_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider("claude-3-5-sonnet-20241022")


def test_anthropic_provider_posts_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured: dict[str, Any] = {}

    def fake_post(
        self: httpx.Client, url: str, *, headers: Any = None, json: Any = None, timeout: Any = None
    ) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        return _FakeResponse(
            {
                "content": [{"type": "text", "text": "hi there"}],
                "usage": {"input_tokens": 7, "output_tokens": 3},
            }
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = AnthropicProvider("claude-3-5-sonnet-20241022")
    with httpx.Client() as client:
        response = provider.complete(system="sys", user="usr", client=client)

    assert response.text == "hi there"
    assert response.input_tokens == 7
    assert response.output_tokens == 3
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"


def test_estimate_cost_usd_known_model() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.15 + 0.6)


def test_estimate_cost_usd_unknown_model_returns_none() -> None:
    assert estimate_cost_usd("some-unlisted-model", 100, 100) is None
