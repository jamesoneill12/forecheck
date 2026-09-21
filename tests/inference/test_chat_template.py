from __future__ import annotations

from typing import Any

import pytest

from forecheck.inference.chat_template import (
    apply_chat_template,
    build_chat_messages,
    plan_chat_prefill,
    render_full_chat_text,
)
from forecheck.inference.prompt import SYSTEM_PREAMBLE


def test_build_chat_messages_wraps_system_and_user() -> None:
    messages = build_chat_messages("ctx", "question?")

    assert messages[0] == {"role": "system", "content": SYSTEM_PREAMBLE}
    assert messages[1] == {"role": "user", "content": "ctx\n\nquestion?"}


class _DirectKwargTokenizer:
    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        enable_thinking: bool,
    ) -> str:
        return f"direct:{enable_thinking}"


class _NestedKwargTokenizer:
    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        chat_template_kwargs: dict[str, Any] | None = None,
    ) -> str:
        thinking = (chat_template_kwargs or {}).get("enable_thinking")
        return f"nested:{thinking}"


class _PlainTokenizer:
    def apply_chat_template(
        self, messages: list[dict[str, str]], *, add_generation_prompt: bool, tokenize: bool
    ) -> str:
        return "plain"


def test_apply_chat_template_prefers_direct_enable_thinking_kwarg() -> None:
    assert apply_chat_template(_DirectKwargTokenizer(), [], enable_thinking=False) == "direct:False"


def test_apply_chat_template_falls_back_to_chat_template_kwargs() -> None:
    result = apply_chat_template(_NestedKwargTokenizer(), [], enable_thinking=False)
    assert result == "nested:False"


def test_apply_chat_template_falls_back_to_plain_rendering() -> None:
    assert apply_chat_template(_PlainTokenizer(), [], enable_thinking=False) == "plain"


class _WordTokenizer:
    """A whitespace-splitting toy tokenizer with a real (non-merging) chat template."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        **kwargs: Any,
    ) -> str:
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
        text = f"<sys>{system}</sys><user>{user}</user>"
        if add_generation_prompt:
            text += "<assistant>"
        return text

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return [hash(w) % 10_000 for w in text.split()] or [0]


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
    """A toy tokenizer whose template puts the question directly against the
    rendered context (no template-owned separator), and whose ``encode`` merges a
    newline immediately followed by ``Q`` into one token -- a stand-in for a BPE merge
    that only happens when the boundary is tokenized jointly rather than split."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
        **kwargs: Any,
    ) -> str:
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
        text = f"{system}|{user}"
        if add_generation_prompt:
            text += "|GEN"
        return text

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ids: list[int] = []
        i = 0
        while i < len(text):
            if text[i : i + 2] == "\nQ":
                ids.append(9999)
                i += 2
                continue
            ids.append(ord(text[i]))
            i += 1
        return ids


def test_plan_chat_prefill_returns_none_when_boundary_tokenization_diverges() -> None:
    tokenizer = _BoundaryMergingTokenizer()

    plan = plan_chat_prefill(tokenizer, "ctx", "Q?")

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
