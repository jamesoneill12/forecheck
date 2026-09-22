from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from forecheck.contracts import AgentIdentity, PolicyStatement, RiskDimension
from tests.inference.conftest import make_context

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")

_STOP_ID = 301
_ALLOW_ID = 302
_MARKER_ID = 303
_WORD_IDS = {"STOP": _STOP_ID, "ALLOW": _ALLOW_ID}


def test_agent_self_module_imports_without_torch() -> None:
    from forecheck.inference import agent_self

    assert hasattr(agent_self, "AgentSelfBackend")
    assert hasattr(agent_self, "AgentSelfBackendConfig")


def test_require_torch_raises_helpful_error_when_missing() -> None:
    if HAS_TORCH:
        pytest.skip("torch is installed; this exercises the missing-torch error path only")
    from forecheck.inference import agent_self

    with pytest.raises(ImportError, match=r"forecheck\[torch\]"):
        agent_self._require_torch()


def test_load_agent_self_config_from_yaml_and_defaults(tmp_path: Path) -> None:
    from forecheck.inference.agent_self import DEFAULT_MODEL_ID, load_agent_self_config

    path = tmp_path / "config.yaml"
    path.write_text(
        "model_id: ibm-granite/granite-3.3-2b-instruct\ndtype: bf16\nbatch_size: 4\n",
        encoding="utf-8",
    )
    config = load_agent_self_config(path)

    assert config.model_id == "ibm-granite/granite-3.3-2b-instruct"
    assert config.batch_size == 4
    assert DEFAULT_MODEL_ID == "ibm-granite/granite-3.3-8b-instruct"


def test_system_prompt_includes_scopes_and_policy_when_not_stripped() -> None:
    from forecheck.inference.agent_self import _system_prompt

    context = make_context(
        agent=AgentIdentity(id="agent-1", delegated_scopes=["billing:refund"]),
        policies=[PolicyStatement(id="p1", text="SECRETPOLICYTEXT must never be violated")],
    )
    prompt = _system_prompt(context, strip_identity=False)

    assert "billing:refund" in prompt
    assert "SECRETPOLICYTEXT" in prompt
    assert context.principal.id in prompt


def test_system_prompt_omits_scopes_and_policy_when_stripped() -> None:
    from forecheck.inference.agent_self import _system_prompt

    context = make_context(
        agent=AgentIdentity(id="agent-1", delegated_scopes=["billing:refund"]),
        policies=[PolicyStatement(id="p1", text="SECRETPOLICYTEXT must never be violated")],
    )
    prompt = _system_prompt(context, strip_identity=True)

    assert "billing:refund" not in prompt
    assert "SECRETPOLICYTEXT" not in prompt
    assert context.principal.id in prompt


def test_parse_verdict_word_prefers_earliest_match() -> None:
    from forecheck.inference.agent_self import _parse_verdict_word

    assert _parse_verdict_word("STOP. This looks unauthorized.") == "STOP"
    assert _parse_verdict_word("ALLOW. This is routine.") == "ALLOW"
    assert _parse_verdict_word("no clear verdict here") == "ALLOW"
    assert _parse_verdict_word("first ALLOW then reconsider: STOP") == "ALLOW"


def test_single_token_ids_skips_multi_token_forms() -> None:
    from forecheck.inference.agent_self import _single_token_ids

    class _Tok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return {"multi": [1, 2], "single": [3]}[text]

    assert _single_token_ids(_Tok(), ("multi", "single")) == {3}

    class _EmptyTok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [1, 2]

    with pytest.raises(ValueError, match="single token"):
        _single_token_ids(_EmptyTok(), ("multi",))


class _FakeTokenizer:
    def __init__(self) -> None:
        self.pad_token_id: int | None = 0
        self.pad_token: str | None = "<pad>"
        self.eos_token = "<eos>"
        self.padding_side = "right"
        self.chat_calls: list[dict[str, Any]] = []

    def _id_for(self, word: str) -> int:
        if word in _WORD_IDS:
            return _WORD_IDS[word]
        if word == "TRIGGERSTOP":
            return _MARKER_ID
        return (hash(word) % 100) + 400

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        if text.strip() in _WORD_IDS:
            return [_WORD_IDS[text.strip()]]
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
        words = {_STOP_ID: "STOP", _ALLOW_ID: "ALLOW"}
        return [" ".join(words.get(int(t), str(int(t))) for t in seq.tolist()) for seq in sequences]


class _FakeModel:
    def __call__(self, input_ids: Any = None, attention_mask: Any = None) -> SimpleNamespace:
        import torch

        batch, _seq = input_ids.shape
        vocab = 500
        logits = torch.zeros((batch, 1, vocab))
        for i in range(batch):
            risky = bool((input_ids[i] == _MARKER_ID).any())
            logits[i, 0, _STOP_ID] = 10.0 if risky else -10.0
            logits[i, 0, _ALLOW_ID] = -10.0 if risky else 10.0
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
            tokens.append([_STOP_ID if risky else _ALLOW_ID] * max_new_tokens)
        return torch.cat([input_ids, torch.tensor(tokens, dtype=torch.long)], dim=1)


def _wired_backend(**config_kwargs: Any) -> Any:
    from forecheck.inference.agent_self import AgentSelfBackend, AgentSelfBackendConfig

    backend = AgentSelfBackend(AgentSelfBackendConfig(**config_kwargs))
    backend._model = _FakeModel()
    backend._tokenizer = _FakeTokenizer()
    backend._device = "cpu"
    backend._stop_ids = {_STOP_ID}
    backend._allow_ids = {_ALLOW_ID}
    return backend


@requires_torch
def test_score_batch_copies_one_scalar_to_every_dimension() -> None:
    from forecheck.contracts import ProposedAction

    backend = _wired_backend()
    risky = make_context(proposed_action=ProposedAction(tool_name="TRIGGERSTOP", arguments={}))
    benign = make_context()
    dims = [RiskDimension.FINANCIAL_COMMITMENT, RiskDimension.UNAUTHORIZED_SCOPE]

    results = backend.score_batch([risky, benign], dims)

    assert results[0].scores[RiskDimension.FINANCIAL_COMMITMENT] > 0.9
    assert results[0].scores[RiskDimension.FINANCIAL_COMMITMENT] == pytest.approx(
        results[0].scores[RiskDimension.UNAUTHORIZED_SCOPE]
    )
    assert results[1].scores[RiskDimension.FINANCIAL_COMMITMENT] < 0.1
    for value in results[0].scores.values():
        assert 0.0 <= value <= 1.0
    for value in results[1].scores.values():
        assert 0.0 <= value <= 1.0


@requires_torch
def test_score_single_matches_score_batch() -> None:
    backend = _wired_backend()
    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    single = backend.score(context, dims)
    batch = backend.score_batch([context], dims)[0]

    for dim in dims:
        assert single.scores[dim] == pytest.approx(batch.scores[dim], abs=1e-5)


@requires_torch
def test_strip_identity_removes_policy_and_scopes_from_rendered_prompt() -> None:
    backend = _wired_backend(strip_identity=True)
    context = make_context(
        agent=AgentIdentity(id="agent-1", delegated_scopes=["billing:refund"]),
        policies=[PolicyStatement(id="p1", text="SECRETPOLICYTEXT must never be violated")],
    )

    backend.score_batch([context], [RiskDimension.POLICY_CONFLICT])

    call = backend._tokenizer.chat_calls[0]
    full_text = " ".join(m["content"] for m in call["messages"])
    assert "SECRETPOLICYTEXT" not in full_text
    assert "billing:refund" not in full_text


@requires_torch
def test_generate_dump_produces_verdict_and_completion() -> None:
    from forecheck.contracts import ProposedAction

    backend = _wired_backend()
    risky = make_context(proposed_action=ProposedAction(tool_name="TRIGGERSTOP", arguments={}))
    benign = make_context()

    results = backend.generate_dump([risky, benign])

    assert results[0]["verdict"] == "STOP"
    assert results[1]["verdict"] == "ALLOW"
    assert "completion" in results[0]


@requires_torch
def test_dump_verdicts_writes_jsonl(tmp_path: Path) -> None:
    from tests.evaluation.conftest import make_example

    backend = _wired_backend()
    example = make_example("ex-1")
    out_path = tmp_path / "dump.jsonl"

    backend.dump_verdicts([example], out_path)

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"example_id": "ex-1", "verdict": "ALLOW", "completion": rows[0]["completion"]}]


def test_render_self_judgment_section_reports_agent_metrics_and_delta() -> None:
    from forecheck.evaluation.metrics import DimensionMetrics, ThresholdMetrics
    from forecheck.evaluation.report import DatasetIdentity, EvaluationClass, EvaluationReport
    from forecheck.inference.agent_self import render_self_judgment_section

    def _report(auprc: float, recall: float) -> EvaluationReport:
        dm = DimensionMetrics(
            dimension=RiskDimension.FINANCIAL_COMMITMENT,
            n_evaluable=10,
            n_positive=5,
            positive_rate=0.5,
            auprc=auprc,
            auroc=0.8,
            brier=0.1,
            nll=0.2,
            ece=0.05,
            adaptive_ece=0.05,
            reliability_bins=(),
            at_threshold=ThresholdMetrics(threshold=0.5, precision=0.5, recall=0.5, f1=0.5),
            at_optimal_threshold=ThresholdMetrics(
                threshold=0.4, precision=0.6, recall=recall, f1=0.6
            ),
            optimal_threshold=0.4,
        )
        return EvaluationReport(
            evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
            dataset=DatasetIdentity(split=None, n=10),
            seed=0,
            created_at=datetime.now(UTC),
            dimensions={RiskDimension.FINANCIAL_COMMITMENT: dm},
            macro={},
            worst_slice={},
        )

    agent_report = _report(auprc=0.5, recall=0.6)
    checker_report = _report(auprc=0.8, recall=0.9)

    section_alone = render_self_judgment_section(agent_report, None)
    assert "Self-judgment vs external checker" in section_alone
    assert "0.5000" in section_alone
    assert "checker auprc" not in section_alone

    section_compared = render_self_judgment_section(agent_report, checker_report)
    assert "0.8000" in section_compared
    assert "-0.3000" in section_compared
