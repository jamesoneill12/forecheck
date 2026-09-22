from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from forecheck.judge.providers import (
    AnthropicProvider,
    CodexCliProvider,
    OpenAICompatProvider,
    estimate_cost_usd,
    provider_for_name,
)


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


def test_estimate_cost_usd_codex_cli_returns_none_even_for_a_priced_model() -> None:
    assert estimate_cost_usd("gpt-4o-mini", 1000, 1000, provider="codex_cli") is None


def test_codex_cli_provider_requires_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORECHECK_CODEX_BIN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="codex CLI not found"):
        CodexCliProvider("gpt-5.6-sol")


def _write_last_message(argv: list[str], content: str) -> None:
    idx = argv.index("--output-last-message")
    Path(argv[idx + 1]).write_text(content, encoding="utf-8")


def test_codex_cli_provider_builds_expected_argv_and_reads_last_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        _write_last_message(argv, '{"ok": true}')
        return subprocess.CompletedProcess(argv, 0, stdout="tokens used: 1,234\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = CodexCliProvider("gpt-5.6-sol", reasoning_effort="medium")
    with httpx.Client() as client:
        response = provider.complete(system="sys prompt", user="user prompt", client=client)

    argv = captured["argv"]
    assert argv[0] == "/usr/local/bin/codex"
    assert argv[-1] == "sys prompt\n\nuser prompt"
    assert argv[1:9] == [
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--cd",
        argv[5],
        "-s",
        "read-only",
        "-m",
    ]
    assert "gpt-5.6-sol" in argv
    assert "-c" in argv
    assert argv[argv.index("-c") + 1] == "model_reasoning_effort=medium"
    assert response.text == '{"ok": true}'
    assert response.output_tokens == 1234
    assert response.input_tokens == 0
    assert captured["kwargs"]["timeout"] == 600.0


def test_codex_cli_provider_reads_token_count_from_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        _write_last_message(argv, "pong")
        return subprocess.CompletedProcess(
            argv, 0, stdout="pong\n", stderr="hook: Stop\ntokens used\n20,558\n"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = CodexCliProvider("gpt-5.6-sol")
    with httpx.Client() as client:
        response = provider.complete(system="sys", user="usr", client=client)

    assert response.output_tokens == 20558


def test_codex_cli_provider_raises_with_stderr_excerpt_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom: auth expired")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = CodexCliProvider("gpt-5.6-sol")
    with httpx.Client() as client, pytest.raises(RuntimeError, match="boom: auth expired"):
        provider.complete(system="sys", user="usr", client=client)


def test_codex_cli_provider_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = CodexCliProvider("gpt-5.6-sol", timeout=5.0)
    with httpx.Client() as client, pytest.raises(RuntimeError, match="timed out after 5"):
        provider.complete(system="sys", user="usr", client=client)


def test_codex_cli_provider_raises_when_last_message_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = CodexCliProvider("gpt-5.6-sol")
    with httpx.Client() as client, pytest.raises(RuntimeError, match="output-last-message"):
        provider.complete(system="sys", user="usr", client=client)


def test_provider_for_name_dispatches_codex_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORECHECK_CODEX_BIN", "/usr/local/bin/codex")
    provider = provider_for_name("codex_cli", "gpt-5.6-sol", reasoning_effort="high")
    assert isinstance(provider, CodexCliProvider)
    assert provider.model == "gpt-5.6-sol"
    assert provider._reasoning_effort == "high"


def test_provider_for_name_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        provider_for_name("not-a-provider", "some-model")
