from __future__ import annotations

import re
from typing import Any

import pytest

from forecheck.inference.chat_template import (
    apply_chat_template,
    build_chat_messages,
    plan_chat_prefill,
    render_full_chat_text,
    thinking_kwargs,
)
from forecheck.inference.prompt import CONTEXT_ACK, SYSTEM_PREAMBLE


def test_build_chat_messages_is_four_messages_system_user_assistant_user() -> None:
    messages = build_chat_messages("ctx", "question?")

    assert messages == [
        {"role": "system", "content": SYSTEM_PREAMBLE},
        {"role": "user", "content": "ctx"},
        {"role": "assistant", "content": CONTEXT_ACK},
        {"role": "user", "content": "question?"},
    ]


class _CapturingTokenizer:
    """Records the messages and kwargs a caller passed to ``apply_chat_template``."""

    def __init__(self, chat_template: str) -> None:
        self.chat_template = chat_template
        self.calls: list[dict[str, Any]] = []

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        **kwargs: Any,
    ) -> str:
        self.calls.append({"messages": messages, **kwargs})
        return "rendered"

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return [hash(w) % 10_000 for w in text.split()] or [0]


@pytest.mark.parametrize(
    ("chat_template", "expected"),
    [
        ("{% if enable_thinking %}...{% endif %}", {"enable_thinking": False}),
        ("{% if thinking %}...{% endif %}", {"thinking": False}),
        ("{{ messages }}", {}),
        ("", {}),
    ],
)
def test_thinking_kwargs_resolves_per_template_convention(
    chat_template: str, expected: dict[str, bool]
) -> None:
    assert thinking_kwargs(_CapturingTokenizer(chat_template)) == expected


def test_thinking_kwargs_missing_chat_template_attribute_returns_empty() -> None:
    class _NoTemplateAttr:
        pass

    assert thinking_kwargs(_NoTemplateAttr()) == {}


def test_apply_chat_template_passes_resolved_thinking_kwarg() -> None:
    tokenizer = _CapturingTokenizer("{% if enable_thinking %}...{% endif %}")

    apply_chat_template(tokenizer, [{"role": "system", "content": "s"}])

    assert tokenizer.calls[-1]["enable_thinking"] is False


def test_apply_chat_template_passes_no_kwarg_when_template_has_no_toggle() -> None:
    tokenizer = _CapturingTokenizer("{{ messages }}")

    apply_chat_template(tokenizer, [{"role": "system", "content": "s"}])

    assert "enable_thinking" not in tokenizer.calls[-1]
    assert "thinking" not in tokenizer.calls[-1]


def test_render_full_chat_text_passes_system_message_first() -> None:
    tokenizer = _CapturingTokenizer("")

    render_full_chat_text(tokenizer, "ctx", "question?")

    assert tokenizer.calls[-1]["messages"][0]["role"] == "system"


_TAG_RE = re.compile(r"(<[^>]+>)")


def _tag_aware_encode(text: str) -> list[int]:
    """Tokenize ``text`` by treating each ``<tag>`` as one atomic token and splitting
    everything else on whitespace -- a stand-in for a real tokenizer's role-header
    special tokens, which never merge with surrounding text."""
    ids: list[int] = []
    for chunk in _TAG_RE.split(text):
        if not chunk:
            continue
        if chunk.startswith("<") and chunk.endswith(">"):
            ids.append(hash(chunk) % 10_000)
        else:
            ids.extend(hash(w) % 10_000 for w in chunk.split())
    return ids or [0]


class _WordTokenizer:
    """A toy tokenizer with a real (non-merging) chat template: renders all four
    message roles with distinct tag markers, and tokenizes those tags atomically."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        **kwargs: Any,
    ) -> str:
        system, user_context, assistant_ack, user_question = (m["content"] for m in messages)
        text = (
            f"<sys>{system}</sys><user>{user_context}</user>"
            f"<asst>{assistant_ack}</asst><user>{user_question}</user>"
        )
        if add_generation_prompt:
            text += "<assistant>"
        return text

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return _tag_aware_encode(text)


def test_plan_chat_prefill_splits_and_verifies_a_clean_boundary() -> None:
    tokenizer = _WordTokenizer()
    plan = plan_chat_prefill(tokenizer, "some context here", "Is this risky?")

    assert plan is not None
    assert plan.prefix_ids + plan.suffix_ids == plan.full_ids
    full_text = render_full_chat_text(tokenizer, "some context here", "Is this risky?")
    assert plan.full_ids == tuple(tokenizer.encode(full_text, add_special_tokens=False))


def test_plan_chat_prefill_prefix_is_stable_across_questions() -> None:
    tokenizer = _WordTokenizer()
    plan_a = plan_chat_prefill(tokenizer, "some context here", "Is this risky?")
    plan_b = plan_chat_prefill(tokenizer, "some context here", "Does this cost money?")

    assert plan_a is not None
    assert plan_b is not None
    assert plan_a.prefix_ids == plan_b.prefix_ids


class _BoundaryMergingTokenizer:
    """A toy tokenizer whose second user role marker (``>``) still merges with an
    immediately following ``I`` when tokenized jointly -- modeling a tokenizer whose
    role-header token is not truly atomic, which is exactly the case
    ``plan_chat_prefill``'s runtime prefix/suffix check must catch and reject."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        **kwargs: Any,
    ) -> str:
        system, user_context, assistant_ack, user_question = (m["content"] for m in messages)
        text = f"{system}|{user_context}|{assistant_ack}|>{user_question}"
        if add_generation_prompt:
            text += "|GEN"
        return text

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ids: list[int] = []
        i = 0
        while i < len(text):
            if text[i : i + 2] == ">I":
                ids.append(9999)
                i += 2
                continue
            ids.append(ord(text[i]))
            i += 1
        return ids


def test_plan_chat_prefill_returns_none_when_boundary_tokenization_diverges() -> None:
    tokenizer = _BoundaryMergingTokenizer()

    plan = plan_chat_prefill(tokenizer, "ctx", "Is it risky?")

    assert plan is None


def test_plan_chat_prefill_succeeds_for_the_same_tokenizer_without_a_boundary_merge() -> None:
    tokenizer = _BoundaryMergingTokenizer()

    plan = plan_chat_prefill(tokenizer, "ctx", "Does this apply?")

    assert plan is not None
    assert plan.prefix_ids + plan.suffix_ids == plan.full_ids


@pytest.mark.parametrize("question", ["Is this risky?", "Does this cost money?"])
def test_render_full_chat_text_includes_context_and_question(question: str) -> None:
    tokenizer = _WordTokenizer()
    text = render_full_chat_text(tokenizer, "some context", question)
    assert "some context" in text
    assert question in text
    assert "<assistant>" in text
