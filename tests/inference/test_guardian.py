from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from forecheck.contracts import PolicyStatement, RiskDimension
from tests.inference.conftest import make_context

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")

_RISK_ID = 201
_NO_RISK_ID = 202
_MARKER_ID = 203
_WORD_IDS = {"unsafe": _RISK_ID, "safe": _NO_RISK_ID, "Yes": _RISK_ID, "No": _NO_RISK_ID}


def test_guardian_module_imports_without_torch() -> None:
    from forecheck.inference import guardian

    assert hasattr(guardian, "GuardianBackend")
    assert hasattr(guardian, "GuardianBackendConfig")


def test_require_torch_raises_helpful_error_when_missing() -> None:
    if HAS_TORCH:
        pytest.skip("torch is installed; this exercises the missing-torch error path only")
    from forecheck.inference import guardian

    with pytest.raises(ImportError, match=r"forecheck\[torch\]"):
        guardian._require_torch()


def test_load_guardian_config_from_yaml(tmp_path: Path) -> None:
    from forecheck.inference.guardian import load_guardian_config

    path = tmp_path / "config.yaml"
    path.write_text(
        "model_id: ibm-granite/granite-guardian-3.3-8b\n"
        "family: granite_guardian\n"
        "dtype: bf16\n"
        "max_tokens: 1024\n"
        "batch_size: 4\n"
        "dimension_definitions:\n"
        "  financial_commitment: custom definition\n",
        encoding="utf-8",
    )
    config = load_guardian_config(path)

    assert config.model_id == "ibm-granite/granite-guardian-3.3-8b"
    assert config.family == "granite_guardian"
    assert config.max_tokens == 1024
    assert config.batch_size == 4
    assert config.dimension_definitions[RiskDimension.FINANCIAL_COMMITMENT] == "custom definition"
    assert config.dimension_definitions[RiskDimension.POLICY_CONFLICT] != "custom definition"


def test_default_dimension_definitions_cover_every_dimension() -> None:
    from forecheck.inference.guardian import DEFAULT_DIMENSION_DEFINITIONS

    assert set(DEFAULT_DIMENSION_DEFINITIONS) == set(RiskDimension)


def test_single_token_ids_skips_multi_token_forms_and_collects_the_rest() -> None:
    from forecheck.inference.guardian import _single_token_ids

    class _Tok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return {"multi": [1, 2], "single": [3], "also-single": [3]}[text]

    ids = _single_token_ids(_Tok(), ("multi", "single", "also-single"))
    assert ids == {3}


def test_single_token_ids_raises_when_nothing_survives() -> None:
    from forecheck.inference.guardian import _single_token_ids

    class _Tok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [1, 2]

    with pytest.raises(ValueError, match="single token"):
        _single_token_ids(_Tok(), ("multi",))


def test_parse_verdict_prefers_the_last_matching_word() -> None:
    from forecheck.inference.guardian import _parse_verdict

    assert _parse_verdict("Policy defines unsafe and safe. Verdict: unsafe") is True
    assert _parse_verdict("Policy defines unsafe and safe. Verdict: safe") is False
    assert _parse_verdict("This action is compliant.") is False
    assert _parse_verdict("This action is a violation of policy.") is True


class _FakeGuardianTokenizer:
    def __init__(self) -> None:
        self.pad_token_id: int | None = 0
        self.pad_token: str | None = "<pad>"
        self.eos_token = "<eos>"
        self.padding_side = "right"
        self.chat_calls: list[dict[str, Any]] = []

    def _id_for(self, word: str) -> int:
        if word in _WORD_IDS:
            return _WORD_IDS[word]
        if word == "TRIGGERRISK":
            return _MARKER_ID
        return (hash(word) % 100) + 300

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        if text in _WORD_IDS:
            return [_WORD_IDS[text]]
        return [self._id_for(w) for w in text.split()] or [1]

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool = False,
        add_generation_prompt: bool = True,
        **kwargs: Any,
    ) -> str:
        self.chat_calls.append({"messages": messages, "kwargs": kwargs})
        text = " ".join(m["content"] for m in messages)
        if "guardian_config" in kwargs:
            text += f" || guardian_config={kwargs['guardian_config']['custom_criteria']}"
        if "categories" in kwargs:
            text += f" || categories={kwargs['categories']['custom']}"
        if add_generation_prompt:
            text += " || GEN"
        return text

    def __call__(
        self,
        texts: list[str],
        return_tensors: str = "pt",
        padding: bool = True,
        truncation: bool = True,
        max_length: int = 4096,
    ) -> dict[str, Any]:
        import torch

        rows = [[self._id_for(w) for w in t.split()][:max_length] or [1] for t in texts]
        width = max(len(r) for r in rows)
        input_ids = torch.full((len(rows), width), self.pad_token_id, dtype=torch.long)
        attention_mask = torch.zeros((len(rows), width), dtype=torch.long)
        for i, row in enumerate(rows):
            if self.padding_side == "left":
                input_ids[i, width - len(row) :] = torch.tensor(row, dtype=torch.long)
                attention_mask[i, width - len(row) :] = 1
            else:
                input_ids[i, : len(row)] = torch.tensor(row, dtype=torch.long)
                attention_mask[i, : len(row)] = 1
        return {"input_ids": input_ids, "attention_mask": attention_mask}

    def batch_decode(self, sequences: Any, skip_special_tokens: bool = True) -> list[str]:
        words = {_RISK_ID: "unsafe", _NO_RISK_ID: "safe"}
        return [" ".join(words.get(int(t), str(int(t))) for t in seq.tolist()) for seq in sequences]


class _FakeGuardianModel:
    """Reads the last-position logit off whether ``_MARKER_ID`` appears in the row."""

    def __init__(self) -> None:
        self.forward_calls = 0

    def __call__(self, input_ids: Any = None, attention_mask: Any = None) -> SimpleNamespace:
        import torch

        self.forward_calls += 1
        batch, _seq = input_ids.shape
        vocab = 400
        logits = torch.zeros((batch, 1, vocab))
        for i in range(batch):
            risky = bool((input_ids[i] == _MARKER_ID).any())
            logits[i, 0, _RISK_ID] = 10.0 if risky else -10.0
            logits[i, 0, _NO_RISK_ID] = -10.0 if risky else 10.0
        return SimpleNamespace(logits=logits)

    def generate(
        self,
        input_ids: Any = None,
        attention_mask: Any = None,
        max_new_tokens: int = 8,
        do_sample: bool = False,
    ) -> Any:
        import torch

        batch, _seq = input_ids.shape
        tokens = []
        for i in range(batch):
            risky = bool((input_ids[i] == _MARKER_ID).any())
            tokens.append([_RISK_ID if risky else _NO_RISK_ID] * max_new_tokens)
        return torch.cat([input_ids, torch.tensor(tokens, dtype=torch.long)], dim=1)


@requires_torch
def test_granite_guardian_prompt_uses_custom_risk_definition_and_tool_call() -> None:
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(
        GuardianBackendConfig(model_id="toy-granite", family="granite_guardian")
    )
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    backend._risk_ids = {_RISK_ID}
    backend._no_risk_ids = {_NO_RISK_ID}

    context = make_context()
    backend.score_batch([context], [RiskDimension.FINANCIAL_COMMITMENT])

    assert len(tokenizer.chat_calls) == 1
    call = tokenizer.chat_calls[0]
    assert "guardian_config" in call["kwargs"]
    definition = call["kwargs"]["guardian_config"]["custom_criteria"]
    assert definition == backend._config.dimension_definitions[RiskDimension.FINANCIAL_COMMITMENT]
    assistant_content = call["messages"][1]["content"]
    assert "issue_refund" in assistant_content


@requires_torch
def test_llama_guard_prompt_uses_single_custom_category() -> None:
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(GuardianBackendConfig(model_id="toy-llama", family="llama_guard"))
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    backend._risk_ids = {_RISK_ID}
    backend._no_risk_ids = {_NO_RISK_ID}

    backend.score_batch([make_context()], [RiskDimension.EXTERNAL_COMMUNICATION])

    call = tokenizer.chat_calls[0]
    assert set(call["kwargs"]["categories"]) == {"custom"}
    assert (
        call["kwargs"]["categories"]["custom"]
        == backend._config.dimension_definitions[RiskDimension.EXTERNAL_COMMUNICATION]
    )


@requires_torch
def test_yes_no_probs_detects_risk_marker_in_context() -> None:
    from forecheck.contracts import ProposedAction
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(
        GuardianBackendConfig(model_id="toy-granite", family="granite_guardian")
    )
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    backend._risk_ids = {_RISK_ID}
    backend._no_risk_ids = {_NO_RISK_ID}

    risky = make_context(proposed_action=ProposedAction(tool_name="TRIGGERRISK", arguments={}))
    benign = make_context()

    results = backend.score_batch([risky, benign], [RiskDimension.FINANCIAL_COMMITMENT])

    assert results[0].scores[RiskDimension.FINANCIAL_COMMITMENT] > 0.9
    assert results[1].scores[RiskDimension.FINANCIAL_COMMITMENT] < 0.1


@requires_torch
def test_gpt_oss_safeguard_scores_by_generation_and_verdict_parse() -> None:
    from forecheck.contracts import ProposedAction
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(
        GuardianBackendConfig(model_id="toy-gpt-oss", family="gpt_oss_safeguard")
    )
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"

    risky = make_context(proposed_action=ProposedAction(tool_name="TRIGGERRISK", arguments={}))
    benign = make_context()

    results = backend.score_batch([risky, benign], [RiskDimension.FINANCIAL_COMMITMENT])

    assert results[0].scores[RiskDimension.FINANCIAL_COMMITMENT] == 1.0
    assert results[1].scores[RiskDimension.FINANCIAL_COMMITMENT] == 0.0
    assert backend.capabilities.deterministic is False


@requires_torch
def test_gpt_oss_safeguard_system_prompt_carries_policy_text() -> None:
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(
        GuardianBackendConfig(model_id="toy-gpt-oss", family="gpt_oss_safeguard")
    )
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"

    context = make_context(
        policies=[PolicyStatement(id="p1", text="SECRETPOLICYTEXT must never be violated")]
    )
    backend.score_batch([context], [RiskDimension.POLICY_CONFLICT])

    assert "SECRETPOLICYTEXT" in tokenizer.chat_calls[0]["messages"][0]["content"]


@requires_torch
def test_strip_identity_removes_policy_text_from_gpt_oss_safeguard_system_prompt() -> None:
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(
        GuardianBackendConfig(
            model_id="toy-gpt-oss", family="gpt_oss_safeguard", strip_identity=True
        )
    )
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"

    context = make_context(
        policies=[PolicyStatement(id="p1", text="SECRETPOLICYTEXT must never be violated")]
    )
    backend.score_batch([context], [RiskDimension.POLICY_CONFLICT])

    assert "SECRETPOLICYTEXT" not in tokenizer.chat_calls[0]["messages"][0]["content"]


@requires_torch
def test_score_single_matches_score_batch() -> None:
    from forecheck.inference.guardian import GuardianBackend, GuardianBackendConfig

    tokenizer = _FakeGuardianTokenizer()
    backend = GuardianBackend(GuardianBackendConfig(model_id="toy-llama", family="llama_guard"))
    backend._model = _FakeGuardianModel()
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    backend._risk_ids = {_RISK_ID}
    backend._no_risk_ids = {_NO_RISK_ID}

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    single = backend.score(context, dims)
    batch = backend.score_batch([context], dims)[0]

    for dim in dims:
        assert single.scores[dim] == pytest.approx(batch.scores[dim], abs=1e-5)
