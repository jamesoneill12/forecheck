"""Chat-template rendering shared by inference and training.

Post-trained instruction models score correctly only via their own chat template.
Both :mod:`forecheck.inference.hf` and :mod:`forecheck.training.dataset` import from
here so the serve and train paths cannot drift. See ADR 0004, Amendments 2026-09-20
and 2026-09-21.

:func:`thinking_kwargs` resolves the thinking-toggle keyword (``enable_thinking``,
``thinking``, or none) from the tokenizer's own template text, since the selected
bases disagree on the keyword; an unrecognised kwarg is silently ignored by
transformers, but resolving the right one keeps the prompt contract explicit.

:func:`build_chat_messages` always supplies an explicit system message so a
template's own date-embedding default (e.g. Granite's) is never reached, keeping the
rendered prompt stable across days.

:func:`plan_chat_prefill` verifies shared-prefill KV-cache reuse is safe by checking
that tokenizing the prefix and suffix separately reproduces the full text's token ids
exactly (a BPE merge can straddle the split point); it returns ``None`` when that
check fails, and callers fall back to a single non-shared forward pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forecheck.inference.prompt import SYSTEM_PREAMBLE

__all__ = [
    "ChatPrefillPlan",
    "apply_chat_template",
    "build_chat_messages",
    "plan_chat_prefill",
    "render_full_chat_text",
    "thinking_kwargs",
]

_SENTINEL = "FORECHECK_QUESTION_SENTINEL"


def build_chat_messages(context_text: str, question: str) -> list[dict[str, str]]:
    """Build the two-message chat payload scored for every dimension.

    The system message is always present, so a template's own default system message
    (which may embed the current date) is never reached.
    """
    return [
        {"role": "system", "content": SYSTEM_PREAMBLE},
        {"role": "user", "content": f"{context_text}\n\n{question}"},
    ]


def thinking_kwargs(tokenizer: Any) -> dict[str, bool]:
    """Resolve the thinking-toggle keyword, if any, this tokenizer's template accepts.

    Inspects ``tokenizer.chat_template`` for the variable name it references:
    ``enable_thinking`` (checked first, since it contains ``thinking`` as a
    substring), then bare ``thinking``, else an empty mapping when the template has no
    thinking toggle at all.
    """
    template = getattr(tokenizer, "chat_template", "") or ""
    if "enable_thinking" in template:
        return {"enable_thinking": False}
    if "thinking" in template:
        return {"thinking": False}
    return {}


def apply_chat_template(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    """Render ``messages`` to text with the generation prompt open.

    Thinking mode is disabled via whichever keyword (if any) :func:`thinking_kwargs`
    resolves for this tokenizer's template.
    """
    return str(
        tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
            **thinking_kwargs(tokenizer),
        )
    )


def render_full_chat_text(tokenizer: Any, context_text: str, question: str) -> str:
    """Render the full chat-templated prompt for one (context, question) pair."""
    return apply_chat_template(tokenizer, build_chat_messages(context_text, question))


@dataclass(frozen=True, slots=True)
class ChatPrefillPlan:
    """A verified split of one rendered chat prompt into a cacheable prefix and a
    per-question suffix: ``prefix_ids + suffix_ids == full_ids`` by construction."""

    prefix_ids: tuple[int, ...]
    suffix_ids: tuple[int, ...]
    full_ids: tuple[int, ...]


def plan_chat_prefill(tokenizer: Any, context_text: str, question: str) -> ChatPrefillPlan | None:
    """Split the chat-templated prompt at the end of the rendered context.

    The split point is located by rendering the template with a sentinel in place of
    the question, then verified by checking that separately tokenizing the prefix and
    the (question + template tail) suffix reproduces the full rendered text's token
    ids exactly. Returns ``None`` when that check fails, signalling that shared-prefix
    caching is not safe for this (tokenizer, template, question) combination.
    """
    sentinel_text = render_full_chat_text(tokenizer, context_text, _SENTINEL)
    split_at = sentinel_text.find(_SENTINEL)
    if split_at == -1:
        return None
    prefix_text = sentinel_text[:split_at]
    template_tail = sentinel_text[split_at + len(_SENTINEL) :]
    suffix_text = question + template_tail

    full_text = render_full_chat_text(tokenizer, context_text, question)
    prefix_ids = tuple(tokenizer.encode(prefix_text, add_special_tokens=False))
    suffix_ids = tuple(tokenizer.encode(suffix_text, add_special_tokens=False))
    full_ids = tuple(tokenizer.encode(full_text, add_special_tokens=False))

    if prefix_ids + suffix_ids != full_ids:
        return None
    return ChatPrefillPlan(prefix_ids=prefix_ids, suffix_ids=suffix_ids, full_ids=full_ids)
