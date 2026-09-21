"""Chat-template rendering shared by inference and training.

Post-trained instruction models score correctly only via their own chat template.
Both :mod:`forecheck.inference.hf` and :mod:`forecheck.training.dataset` import from
here so the serve and train paths cannot drift. See ADR 0004, Amendments 2026-09-20,
2026-09-21 (a) and 2026-09-21 (b).

:func:`thinking_kwargs` resolves the thinking-toggle keyword from the tokenizer's own
template text, since the selected bases disagree on it.

:func:`build_chat_messages` renders four messages -- system, user (context), assistant
(fixed acknowledgement), user (question) -- instead of packing context and question
into one user turn, so the shared-prefill split in :func:`plan_chat_prefill` lands on
the second user turn's role-header special token rather than on plain text a BPE merge
can straddle (observed on ``granite-3.3-2b-instruct`` for a question starting "Is").

:func:`plan_chat_prefill` still verifies the split by re-tokenizing prefix and suffix
separately and comparing to the full tokenization, returning ``None`` -- triggering a
non-shared fallback -- on any mismatch, as a safety net.

:class:`ChatPrefillPlanner` caches that sentinel render per context (single entry,
since callers iterate questions inside a context loop) and the prefix-match verdict
per ``(question, template_tail)`` with no eviction on context change, since the
verdict depends only on the tokenizer's template and the question, never on context
text. ``plan_chat_prefill`` wraps a fresh, single-use planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forecheck.inference.prompt import CONTEXT_ACK, SYSTEM_PREAMBLE

__all__ = [
    "ChatPrefillPlan",
    "ChatPrefillPlanner",
    "apply_chat_template",
    "build_chat_messages",
    "plan_chat_prefill",
    "render_full_chat_text",
    "thinking_kwargs",
]

_SENTINEL = "FORECHECK_QUESTION_SENTINEL"


def build_chat_messages(context_text: str, question: str) -> list[dict[str, str]]:
    """Build the four-message chat payload scored for every dimension.

    ``[system: SYSTEM_PREAMBLE] [user: context_text] [assistant: CONTEXT_ACK] [user:
    question]``. The system message is always present, so a template's own default
    system message (which may embed the current date) is never reached. Splitting the
    context and question across two user turns, with a fixed assistant turn between
    them, puts the shared-prefill boundary on the second user turn's role-header
    special token instead of on plain text, so a BPE merge cannot straddle it (see the
    module docstring).
    """
    return [
        {"role": "system", "content": SYSTEM_PREAMBLE},
        {"role": "user", "content": context_text},
        {"role": "assistant", "content": CONTEXT_ACK},
        {"role": "user", "content": question},
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


class ChatPrefillPlanner:
    """Plans :class:`ChatPrefillPlan` splits for many questions against a sequence of
    contexts, at a fraction of :func:`plan_chat_prefill`'s per-call rendering cost.

    Holds a single-entry cache of the last context's sentinel render (prefix_text,
    prefix_ids, template_tail), refreshed only when ``context_text`` changes, plus a
    ``(question, template_tail)``-keyed cache of ``suffix_ids`` and the prefix-match
    verdict that is never evicted on context change, since that verdict does not
    depend on context (see the module docstring).
    """

    def __init__(self, tokenizer: Any) -> None:
        self._tokenizer = tokenizer
        self._context_text: str | None = None
        self._prefix_ids: tuple[int, ...] | None = None
        self._template_tail: str | None = None
        self._suffix_ids_cache: dict[tuple[str, str], tuple[int, ...]] = {}
        self._verdicts: dict[tuple[str, str], bool] = {}

    def _load_context(self, context_text: str) -> None:
        self._context_text = context_text
        sentinel_text = render_full_chat_text(self._tokenizer, context_text, _SENTINEL)
        split_at = sentinel_text.find(_SENTINEL)
        if split_at == -1:
            self._prefix_ids = None
            self._template_tail = None
            return
        prefix_text = sentinel_text[:split_at]
        self._prefix_ids = tuple(self._tokenizer.encode(prefix_text, add_special_tokens=False))
        self._template_tail = sentinel_text[split_at + len(_SENTINEL) :]

    def plan(self, context_text: str, question: str) -> ChatPrefillPlan | None:
        """Split the chat-templated prompt just before the question turn's content.

        See :func:`plan_chat_prefill` for the splitting and verification strategy;
        this only adds caching around the same logic.
        """
        if context_text != self._context_text:
            self._load_context(context_text)
        prefix_ids = self._prefix_ids
        template_tail = self._template_tail
        if prefix_ids is None or template_tail is None:
            return None

        cache_key = (question, template_tail)
        if self._verdicts.get(cache_key) is False:
            return None

        suffix_ids = self._suffix_ids_cache.get(cache_key)
        if suffix_ids is None:
            suffix_text = question + template_tail
            suffix_ids = tuple(self._tokenizer.encode(suffix_text, add_special_tokens=False))
            self._suffix_ids_cache[cache_key] = suffix_ids

        if cache_key not in self._verdicts:
            full_text = render_full_chat_text(self._tokenizer, context_text, question)
            full_ids = tuple(self._tokenizer.encode(full_text, add_special_tokens=False))
            self._verdicts[cache_key] = prefix_ids + suffix_ids == full_ids

        if not self._verdicts[cache_key]:
            return None
        return ChatPrefillPlan(
            prefix_ids=prefix_ids, suffix_ids=suffix_ids, full_ids=prefix_ids + suffix_ids
        )


def plan_chat_prefill(tokenizer: Any, context_text: str, question: str) -> ChatPrefillPlan | None:
    """Split the chat-templated prompt just before the question turn's content.

    The split point is located by rendering the template with a sentinel in place of
    the question, then verified by checking that separately tokenizing the prefix and
    the (question + template tail) suffix reproduces the full rendered text's token
    ids exactly. Returns ``None`` when that check fails, signalling that shared-prefix
    caching is not safe for this (tokenizer, template, question) combination. Builds a
    fresh, single-use :class:`ChatPrefillPlanner` per call; callers planning more than
    one (context, question) pair should build their own planner and reuse it instead.
    """
    return ChatPrefillPlanner(tokenizer).plan(context_text, question)
