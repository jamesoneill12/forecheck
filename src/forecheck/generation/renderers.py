"""Renderer protocol and implementations.

Every renderer turns a :class:`~forecheck.contracts.latent.LatentScenario` into an
:class:`~forecheck.contracts.context.ActionContext`. The offline renderer is pure
Python and template-driven; the LLM renderer delegates only the natural-language
surface to a model, then reuses the exact same assembly code so that every typed,
label-relevant field still comes straight from the latent scenario.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Callable
from typing import Literal, Protocol, runtime_checkable

from forecheck.contracts import ActionContext, LatentScenario
from forecheck.data.rendering import OfflineTemplateRenderer, SurfaceText, assemble_action_context

__all__ = ["LLMRenderer", "OfflineTemplateRenderer", "Renderer"]

_ANTHROPIC_ENV_VAR = "ANTHROPIC_API_KEY"
_OPENAI_ENV_VAR = "OPENAI_API_KEY"

_ENV_VAR_FOR_PROVIDER: dict[str, str] = {
    "anthropic": _ANTHROPIC_ENV_VAR,
    "openai": _OPENAI_ENV_VAR,
}


@runtime_checkable
class Renderer(Protocol):
    """Anything that can turn a latent scenario into an :class:`ActionContext`.

    Members are declared as read-only properties so a frozen-dataclass implementer
    (e.g. :class:`OfflineTemplateRenderer`) satisfies the protocol structurally.
    """

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def requires_network(self) -> bool: ...

    def render(self, latent: LatentScenario, rng: random.Random) -> ActionContext: ...


def _build_surface_prompt(latent: LatentScenario) -> str:
    return (
        "Render natural-language surface text for a synthetic AI-agent action-review "
        "example. Respond with a single JSON object with exactly these keys: "
        '"objective_text" (string, the human principal\'s request), '
        '"tool_description" (string), "observation_text" (string or null, only set '
        'when untrusted content is present), and "policy_texts" (array of strings, '
        "one per supplied policy predicate, may be empty). Do not include any other "
        "keys or commentary.\n\n"
        f"tool_name={latent.tool.name!r} operation={latent.operation.value!r} "
        f"resource_kind={latent.tool.resource_kind.value!r} "
        f"untrusted_content_present={latent.untrusted_content_present!r} "
        f"untrusted_content_contains_instruction={latent.untrusted_content_contains_instruction!r} "
        f"n_policy_predicates={len(latent.policy_predicates)}"
    )


def _parse_surface_json(raw: str) -> SurfaceText:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM renderer output was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM renderer output must be a JSON object")
    required_keys = {"objective_text", "tool_description", "observation_text", "policy_texts"}
    missing = required_keys - payload.keys()
    if missing:
        raise ValueError(f"LLM renderer output is missing keys: {sorted(missing)}")
    objective_text = payload["objective_text"]
    tool_description = payload["tool_description"]
    observation_text = payload["observation_text"]
    policy_texts = payload["policy_texts"]
    if not isinstance(objective_text, str) or not isinstance(tool_description, str):
        raise ValueError("objective_text and tool_description must be strings")
    if observation_text is not None and not isinstance(observation_text, str):
        raise ValueError("observation_text must be a string or null")
    if not isinstance(policy_texts, list) or not all(isinstance(p, str) for p in policy_texts):
        raise ValueError("policy_texts must be an array of strings")
    return SurfaceText(
        objective_text=objective_text,
        tool_description=tool_description,
        observation_text=observation_text,
        policy_texts=tuple(policy_texts),
    )


class LLMRenderer:
    """Renders surface text via an injected chat function, then assembles the
    :class:`ActionContext` through the same code path as :class:`OfflineTemplateRenderer`.

    Credentials are never accepted directly: the relevant API-key environment variable
    must already be set, or construction fails loudly naming the missing variable.
    """

    requires_network: bool = True

    def __init__(
        self,
        chat_fn: Callable[[str], str],
        *,
        provider: Literal["anthropic", "openai"] = "anthropic",
        model: str = "claude-opus-4-6",
        version: str = "1.0.0",
    ) -> None:
        env_var = _ENV_VAR_FOR_PROVIDER[provider]
        if not os.environ.get(env_var):
            raise RuntimeError(
                f"LLMRenderer requires the {env_var} environment variable to be set; "
                "it never accepts credentials directly and never falls back silently."
            )
        self._chat_fn = chat_fn
        self._model = model
        self.name = f"llm:{provider}:{model}"
        self.version = version

    def render(self, latent: LatentScenario, rng: random.Random) -> ActionContext:
        raw = self._chat_fn(_build_surface_prompt(latent))
        surface = _parse_surface_json(raw)
        return assemble_action_context(latent, rng, surface)
