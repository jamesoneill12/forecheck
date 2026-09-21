"""Chat-template rendering shared by inference and training.

Post-trained instruction models such as Qwen3.5 score correctly only when the context
and question are wrapped in the model's own chat template (and, for Qwen3.5, with
thinking mode explicitly turned off) -- feeding raw context+question text the way
:mod:`forecheck.inference.prompt` alone renders it silently shifts the score
distribution away from what the model was post-trained to expect. Both
:mod:`forecheck.inference.hf` and :mod:`forecheck.training.dataset` import
:func:`plan_chat_prefill`/:func:`render_full_chat_text` from here so the serve and
train paths cannot drift apart. See ADR 0004, Amendment 2026-09-20.

Shared-prefill KV-cache reuse requires that tokenizing ``prefix_text`` and then
tokenizing the per-question suffix produces the same token ids, concatenated, as
tokenizing the full rendered text in one pass. This does not hold for every
tokenizer/template pair -- a BPE merge can straddle the split point -- so the split is
verified before it is trusted: a sentinel is rendered in place of the question to
locate the split point textually, and the resulting prefix/suffix token ids are
checked to reproduce the ids of tokenizing the real, full rendered text exactly. When
the check fails, :func:`plan_chat_prefill` returns ``None`` and callers must fall back
to a single, non-shared forward pass for that question.
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
]

_SENTINEL = "FORECHECK_QUESTION_SENTINEL"


def build_chat_messages(context_text: str, question: str) -> list[dict[str, str]]:
    """Build the two-message chat payload scored for every dimension."""
    return [
        {"role": "system", "content": SYSTEM_PREAMBLE},
        {"role": "user", "content": f"{context_text}\n\n{question}"},
    ]


def apply_chat_template(
    tokenizer: Any, messages: list[dict[str, str]], *, enable_thinking: bool = False
) -> str:
    """Render ``messages`` to text with the generation prompt open, thinking disabled.

    ``enable_thinking`` is passed three ways in order, so this works whether a
    template accepts it as a direct keyword (Qwen's convention), nested under
    ``chat_template_kwargs`` (an alternate convention some templates expose), or not
    at all (in which case the template's own default applies).
    """
    try:
        return str(
            tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False,
                enable_thinking=enable_thinking,
            )
        )
    except TypeError:
        pass
    try:
        return str(
            tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False,
                chat_template_kwargs={"enable_thinking": enable_thinking},
            )
        )
    except TypeError:
        return str(
            tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        )


def render_full_chat_text(
    tokenizer: Any, context_text: str, question: str, *, enable_thinking: bool = False
) -> str:
    """Render the full chat-templated prompt for one (context, question) pair."""
    return apply_chat_template(
        tokenizer, build_chat_messages(context_text, question), enable_thinking=enable_thinking
    )


@dataclass(frozen=True, slots=True)
class ChatPrefillPlan:
    """A verified split of one rendered chat prompt into a cacheable prefix and a
    per-question suffix: ``prefix_ids + suffix_ids == full_ids`` by construction."""

    prefix_ids: tuple[int, ...]
    suffix_ids: tuple[int, ...]
    full_ids: tuple[int, ...]


def plan_chat_prefill(
    tokenizer: Any, context_text: str, question: str, *, enable_thinking: bool = False
) -> ChatPrefillPlan | None:
    """Split the chat-templated prompt at the end of the rendered context.

    The split point is located by rendering the template with a sentinel in place of
    the question, then verified by checking that separately tokenizing the prefix and
    the (question + template tail) suffix reproduces the full rendered text's token
    ids exactly. Returns ``None`` when that check fails, signalling that shared-prefix
    caching is not safe for this (tokenizer, template, question) combination.
    """
    sentinel_text = render_full_chat_text(
        tokenizer, context_text, _SENTINEL, enable_thinking=enable_thinking
    )
    split_at = sentinel_text.find(_SENTINEL)
    if split_at == -1:
        return None
    prefix_text = sentinel_text[:split_at]
    template_tail = sentinel_text[split_at + len(_SENTINEL) :]
    suffix_text = question + template_tail

    full_text = render_full_chat_text(
        tokenizer, context_text, question, enable_thinking=enable_thinking
    )
    prefix_ids = tuple(tokenizer.encode(prefix_text, add_special_tokens=False))
    suffix_ids = tuple(tokenizer.encode(suffix_text, add_special_tokens=False))
    full_ids = tuple(tokenizer.encode(full_text, add_special_tokens=False))

    if prefix_ids + suffix_ids != full_ids:
        return None
    return ChatPrefillPlan(prefix_ids=prefix_ids, suffix_ids=suffix_ids, full_ids=full_ids)
