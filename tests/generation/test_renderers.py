from __future__ import annotations

import random

import pytest

from forecheck.generation.renderers import LLMRenderer, OfflineTemplateRenderer, Renderer
from tests.data.factories import make_latent


def test_offline_renderer_satisfies_the_protocol() -> None:
    renderer: Renderer = OfflineTemplateRenderer()
    assert renderer.requires_network is False
    assert isinstance(renderer.name, str)
    assert isinstance(renderer.version, str)


def test_llm_renderer_requires_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        LLMRenderer(chat_fn=lambda _prompt: "{}")


def test_llm_renderer_never_falls_back_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        LLMRenderer(chat_fn=lambda _prompt: "{}", provider="openai")


def test_llm_renderer_renders_via_injected_chat_fn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def fake_chat(_prompt: str) -> str:
        return (
            '{"objective_text": "Please read the message.", '
            '"tool_description": "Reads a message.", '
            '"observation_text": null, "policy_texts": []}'
        )

    renderer = LLMRenderer(chat_fn=fake_chat)
    latent = make_latent()
    context = renderer.render(latent, random.Random(0))
    assert context.objective.text == "Please read the message."
    assert context.proposed_action.tool_name == latent.tool.name
    assert renderer.requires_network is True


def test_llm_renderer_rejects_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    renderer = LLMRenderer(chat_fn=lambda _prompt: "not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        renderer.render(make_latent(), random.Random(0))


def test_llm_renderer_rejects_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    renderer = LLMRenderer(chat_fn=lambda _prompt: "{}")
    with pytest.raises(ValueError, match="missing keys"):
        renderer.render(make_latent(), random.Random(0))
