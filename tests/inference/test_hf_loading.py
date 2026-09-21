from __future__ import annotations

import sys
import types
from typing import Any, ClassVar

import pytest


class _FakeAutoModelForCausalLM:
    calls: ClassVar[list[tuple[str, dict[str, Any]]]] = []

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: Any) -> str:
        cls.calls.append((model_id, kwargs))
        return "causal-lm-model"


class _FailingAutoModelForCausalLM:
    calls: ClassVar[list[tuple[str, dict[str, Any]]]] = []

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: Any) -> str:
        cls.calls.append((model_id, kwargs))
        raise ValueError(f"Unrecognized configuration class for AutoModelForCausalLM: {model_id}")


class _FakeAutoModelForImageTextToText:
    calls: ClassVar[list[tuple[str, dict[str, Any]]]] = []

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: Any) -> str:
        cls.calls.append((model_id, kwargs))
        return "image-text-to-text-model"


class _FakeAutoTokenizer:
    @classmethod
    def from_pretrained(cls, model_id: str, revision: str | None = None) -> str:
        return "tokenizer"


class _FailingAutoTokenizer:
    @classmethod
    def from_pretrained(cls, model_id: str, revision: str | None = None) -> str:
        raise ValueError(f"no tokenizer for {model_id}")


class _FakeAutoProcessor:
    @classmethod
    def from_pretrained(cls, model_id: str, revision: str | None = None) -> Any:
        return types.SimpleNamespace(tokenizer="processor-tokenizer")


def _install_fake_transformers(monkeypatch: pytest.MonkeyPatch, **attrs: Any) -> None:
    fake_module = types.SimpleNamespace(**attrs)
    monkeypatch.setitem(sys.modules, "transformers", fake_module)


def test_load_model_auto_uses_causal_lm_when_it_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_transformers(
        monkeypatch,
        AutoModelForCausalLM=_FakeAutoModelForCausalLM,
        AutoModelForImageTextToText=_FakeAutoModelForImageTextToText,
    )
    from forecheck.inference.hf_loading import load_model

    result = load_model("some/model", load_class="auto")

    assert result == "causal-lm-model"


def test_load_model_auto_falls_back_to_image_text_to_text_on_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FailingAutoModelForCausalLM.calls = []
    _FakeAutoModelForImageTextToText.calls = []
    _install_fake_transformers(
        monkeypatch,
        AutoModelForCausalLM=_FailingAutoModelForCausalLM,
        AutoModelForImageTextToText=_FakeAutoModelForImageTextToText,
    )
    from forecheck.inference.hf_loading import load_model

    result = load_model("Qwen/Qwen3.5-9B", load_class="auto", torch_dtype="bf16")

    assert result == "image-text-to-text-model"
    assert _FailingAutoModelForCausalLM.calls == [("Qwen/Qwen3.5-9B", {"torch_dtype": "bf16"})]
    assert _FakeAutoModelForImageTextToText.calls == [("Qwen/Qwen3.5-9B", {"torch_dtype": "bf16"})]


def test_load_model_causal_lm_never_tries_image_text_to_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_transformers(
        monkeypatch,
        AutoModelForCausalLM=_FakeAutoModelForCausalLM,
        AutoModelForImageTextToText=_FakeAutoModelForImageTextToText,
    )
    from forecheck.inference.hf_loading import load_model

    result = load_model("some/model", load_class="causal_lm")

    assert result == "causal-lm-model"


def test_load_model_image_text_to_text_skips_causal_lm(monkeypatch: pytest.MonkeyPatch) -> None:
    _FailingAutoModelForCausalLM.calls = []
    _install_fake_transformers(
        monkeypatch,
        AutoModelForCausalLM=_FailingAutoModelForCausalLM,
        AutoModelForImageTextToText=_FakeAutoModelForImageTextToText,
    )
    from forecheck.inference.hf_loading import load_model

    result = load_model("some/model", load_class="image_text_to_text")

    assert result == "image-text-to-text-model"
    assert _FailingAutoModelForCausalLM.calls == []


def test_load_tokenizer_uses_auto_tokenizer_when_it_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_transformers(monkeypatch, AutoTokenizer=_FakeAutoTokenizer)
    from forecheck.inference.hf_loading import load_tokenizer

    assert load_tokenizer("some/model") == "tokenizer"


def test_load_tokenizer_falls_back_to_processor_tokenizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_transformers(
        monkeypatch, AutoTokenizer=_FailingAutoTokenizer, AutoProcessor=_FakeAutoProcessor
    )
    from forecheck.inference.hf_loading import load_tokenizer

    assert load_tokenizer("some/model") == "processor-tokenizer"
