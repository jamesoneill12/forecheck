"""httpx-based chat-completion providers for the LLM judge, plus a subprocess-based
provider that shells out to a locally installed Codex CLI.

Credentials for the httpx providers come only from environment variables
(``OPENAI_API_KEY``, ``OPENAI_BASE_URL``, ``ANTHROPIC_API_KEY``) -- never hard-coded,
never logged, never included in an exception message. ``codex_cli`` needs no API key:
it relies on the operator's own ``codex`` CLI login.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

__all__ = [
    "AnthropicProvider",
    "CodexCliProvider",
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


_CODEX_TOKENS_USED_RE = re.compile(r"tokens used:?\s*([\d,]+)", re.IGNORECASE)


def _parse_codex_tokens_used(stdout: str) -> int:
    match = _CODEX_TOKENS_USED_RE.search(stdout)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


class CodexCliProvider:
    """Shells out to a locally installed, already-logged-in Codex CLI.

    No API key is used or required; the CLI authenticates against the operator's own
    ChatGPT login. Each call runs in a fresh scratch directory (``--cd``) so codex never
    reads repository files, and reads the model's final message from the
    ``--output-last-message`` file rather than parsing stdout.
    """

    def __init__(
        self,
        model: str,
        *,
        reasoning_effort: str = "low",
        timeout: float = 120.0,
    ) -> None:
        binary = os.environ.get("FORECHECK_CODEX_BIN") or shutil.which("codex")
        if not binary:
            raise RuntimeError("codex CLI not found on PATH; install it or set FORECHECK_CODEX_BIN")
        self.model = model
        self._binary = binary
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse:
        del client  # codex_cli talks to a local subprocess, not an httpx client
        prompt = f"{system}\n\n{user}"
        with tempfile.TemporaryDirectory(prefix="forecheck-codex-") as scratch_dir:
            output_path = Path(scratch_dir) / "last-message.txt"
            argv = [
                self._binary,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--cd",
                scratch_dir,
                "-s",
                "read-only",
                "-m",
                self.model,
                "-c",
                f"model_reasoning_effort={self._reasoning_effort}",
                "--output-last-message",
                str(output_path),
                prompt,
            ]
            try:
                result = subprocess.run(  # noqa: S603
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"codex CLI timed out after {self._timeout}s") from exc
            if result.returncode != 0:
                stderr_excerpt = result.stderr.strip()[-2000:]
                raise RuntimeError(f"codex CLI exited {result.returncode}: {stderr_excerpt}")
            if not output_path.exists():
                raise RuntimeError("codex CLI did not write an --output-last-message file")
            text = output_path.read_text(encoding="utf-8")
        return ProviderResponse(
            text=text,
            input_tokens=0,
            output_tokens=_parse_codex_tokens_used(result.stdout + "\n" + result.stderr),
        )


def provider_for_name(name: str, model: str, *, reasoning_effort: str = "low") -> JudgeProvider:
    if name == "openai_compat":
        return OpenAICompatProvider(model)
    if name == "anthropic":
        return AnthropicProvider(model)
    if name == "codex_cli":
        return CodexCliProvider(model, reasoning_effort=reasoning_effort)
    raise ValueError(f"unknown provider {name!r}, expected openai_compat|anthropic|codex_cli")


_PRICING_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4o": (2.5, 10.0),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4.1": (2.0, 8.0),
    "claude-3-5-haiku": (0.8, 4.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-opus": (15.0, 75.0),
}


def estimate_cost_usd(
    model: str, input_tokens: int, output_tokens: int, *, provider: str | None = None
) -> float | None:
    """Approximate USD cost for one completion, or ``None`` if ``model`` has no known price.

    ``codex_cli`` always returns ``None``: it bills against the operator's ChatGPT plan,
    not metered per-token API pricing, so no dollar figure applies.
    """
    if provider == "codex_cli":
        return None
    for prefix, (in_price, out_price) in _PRICING_PER_1M_TOKENS.items():
        if model.startswith(prefix):
            return input_tokens / 1_000_000 * in_price + output_tokens / 1_000_000 * out_price
    return None
