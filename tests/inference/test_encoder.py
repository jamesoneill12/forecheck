from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from forecheck.contracts import RiskDimension
from tests.inference.conftest import make_context

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")


def test_encoder_module_imports_without_torch() -> None:
    from forecheck.inference import encoder

    assert hasattr(encoder, "EncoderBackend")
    assert hasattr(encoder, "EncoderBackendConfig")


def test_require_torch_raises_helpful_error_when_missing() -> None:
    if HAS_TORCH:
        pytest.skip("torch is installed; this exercises the missing-torch error path only")
    from forecheck.inference import encoder

    with pytest.raises(ImportError, match=r"forecheck\[train\]"):
        encoder._require_torch()


def _write_head_config(
    run_dir: Path,
    *,
    model_id: str = "toy-encoder",
    pooling: str = "mean",
    max_tokens: int = 512,
) -> Path:
    checkpoint_dir = run_dir / "checkpoints" / "best"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    head_config = {
        "dimension_order": [d.value for d in RiskDimension],
        "pooling": pooling,
        "model_id": model_id,
        "max_tokens": max_tokens,
        "serialization_contract_hash": "deadbeef",
    }
    path = checkpoint_dir / "head_config.json"
    path.write_text(json.dumps(head_config), encoding="utf-8")
    return checkpoint_dir


def test_resolve_backend_builds_encoder_backend_from_synthetic_run_dir(tmp_path: Path) -> None:
    from forecheck.cli_cmds._common import resolve_backend
    from forecheck.inference.encoder import EncoderBackend

    run_dir = tmp_path / "run"
    _write_head_config(run_dir, model_id="answerdotai/ModernBERT-large", pooling="mean")

    backend = resolve_backend("encoder", run_dir)

    assert isinstance(backend, EncoderBackend)
    assert backend.model_info.backend == "encoder"
    assert backend.model_info.model_id == "answerdotai/ModernBERT-large"
    assert backend.model_info.adapter_id == str(run_dir)


def test_resolve_backend_encoder_requires_head_config(tmp_path: Path) -> None:
    import typer

    from forecheck.cli_cmds._common import resolve_backend

    with pytest.raises(typer.BadParameter, match="requires"):
        resolve_backend("encoder", tmp_path / "missing-run")


@requires_torch
def test_pool_hidden_states_mean_matches_manual_average() -> None:
    import torch

    from forecheck.inference.encoder import pool_hidden_states

    hidden = torch.tensor([[[1.0, 1.0], [3.0, 3.0], [99.0, 99.0]]])
    mask = torch.tensor([[1.0, 1.0, 0.0]])

    pooled = pool_hidden_states(torch, hidden, mask, "mean")

    assert pooled[0].tolist() == pytest.approx([2.0, 2.0])


@requires_torch
def test_pool_hidden_states_cls_takes_first_token() -> None:
    import torch

    from forecheck.inference.encoder import pool_hidden_states

    hidden = torch.tensor([[[7.0, 8.0], [1.0, 1.0]]])
    mask = torch.tensor([[1.0, 1.0]])

    pooled = pool_hidden_states(torch, hidden, mask, "cls")

    assert pooled[0].tolist() == pytest.approx([7.0, 8.0])


if HAS_TORCH:
    import torch as _torch

    class _ToyEncoder(_torch.nn.Module):  # type: ignore[misc]
        """A tiny bidirectional stand-in for an ``AutoModel`` backbone: embeds tokens
        and returns them unchanged as ``last_hidden_state``, so pooling is exactly
        predictable from ``input_ids``."""

        def __init__(self, vocab_size: int, hidden_size: int) -> None:
            super().__init__()
            self.embed = _torch.nn.Embedding(vocab_size, hidden_size)

        def forward(self, input_ids: Any, attention_mask: Any) -> Any:
            from types import SimpleNamespace

            return SimpleNamespace(last_hidden_state=self.embed(input_ids))


class _ToyEncoderTokenizer:
    def __call__(
        self,
        texts: list[str],
        return_tensors: str = "pt",
        truncation: bool = True,
        padding: bool = True,
        max_length: int = 512,
    ) -> dict[str, Any]:
        import torch

        rows = [[self._id_for(w) for w in text.split()][:max_length] or [0] for text in texts]
        width = max(len(r) for r in rows)
        input_ids = torch.zeros((len(rows), width), dtype=torch.long)
        attention_mask = torch.zeros((len(rows), width), dtype=torch.long)
        for i, row in enumerate(rows):
            input_ids[i, : len(row)] = torch.tensor(row, dtype=torch.long)
            attention_mask[i, : len(row)] = 1
        return {"input_ids": input_ids, "attention_mask": attention_mask}

    @staticmethod
    def _id_for(word: str) -> int:
        return (hash(word) % 60) + 4


@requires_torch
def test_encoder_backend_score_batch_produces_one_score_per_context() -> None:
    import torch

    from forecheck.inference.encoder import EncoderBackend, EncoderBackendConfig

    hidden_size = 8
    backbone = _ToyEncoder(vocab_size=64, hidden_size=hidden_size)
    backbone.eval()
    tokenizer = _ToyEncoderTokenizer()

    backend = EncoderBackend(
        EncoderBackendConfig(model_id="toy-encoder", run_dir=Path("unused-run-dir"))
    )
    backend._backbone = backbone
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    backend._head_weight = torch.zeros((len(RiskDimension), hidden_size))
    backend._head_bias = torch.arange(len(RiskDimension), dtype=torch.float32)
    backend._dimension_order = tuple(RiskDimension)
    backend._serialization_contract_hash = "deadbeef"

    contexts = [make_context(), make_context()]
    results = backend.score_batch(contexts)

    assert len(results) == 2
    for result in results:
        for i, dimension in enumerate(RiskDimension):
            assert result.scores[dimension] == pytest.approx(float(i))


@requires_torch
def test_encoder_backend_strip_identity_shrinks_prompt_tokens() -> None:
    import torch

    from forecheck.contracts import AgentIdentity, Principal
    from forecheck.inference.encoder import EncoderBackend, EncoderBackendConfig

    hidden_size = 8
    backbone = _ToyEncoder(vocab_size=64, hidden_size=hidden_size)
    backbone.eval()
    tokenizer = _ToyEncoderTokenizer()

    def _build(strip_identity: bool) -> EncoderBackend:
        backend = EncoderBackend(
            EncoderBackendConfig(
                model_id="toy-encoder",
                run_dir=Path("unused-run-dir"),
                strip_identity=strip_identity,
            )
        )
        backend._backbone = backbone
        backend._tokenizer = tokenizer
        backend._device = "cpu"
        backend._head_weight = torch.zeros((len(RiskDimension), hidden_size))
        backend._head_bias = torch.zeros(len(RiskDimension))
        backend._dimension_order = tuple(RiskDimension)
        backend._serialization_contract_hash = "deadbeef"
        return backend

    context = make_context(
        principal=Principal(id="user-1", entitlements=["billing:refund:<=500", "billing:view"]),
        agent=AgentIdentity(id="agent-1", delegated_scopes=["billing:refund"]),
    )

    full_result = _build(strip_identity=False).score_batch([context])[0]
    stripped_result = _build(strip_identity=True).score_batch([context])[0]

    assert stripped_result.prompt_tokens is not None and full_result.prompt_tokens is not None
    assert stripped_result.prompt_tokens < full_result.prompt_tokens


@requires_torch
def test_encoder_backend_score_single_matches_score_batch() -> None:
    import torch

    from forecheck.inference.encoder import EncoderBackend, EncoderBackendConfig

    hidden_size = 4
    backbone = _ToyEncoder(vocab_size=64, hidden_size=hidden_size)
    backbone.eval()
    tokenizer = _ToyEncoderTokenizer()

    backend = EncoderBackend(
        EncoderBackendConfig(model_id="toy-encoder", run_dir=Path("unused-run-dir"))
    )
    backend._backbone = backbone
    backend._tokenizer = tokenizer
    backend._device = "cpu"
    torch.manual_seed(0)
    backend._head_weight = torch.randn((len(RiskDimension), hidden_size))
    backend._head_bias = torch.randn(len(RiskDimension))
    backend._dimension_order = tuple(RiskDimension)
    backend._serialization_contract_hash = "deadbeef"

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    single = backend.score(context, dims)
    batch = backend.score_batch([context], dims)[0]

    for dim in dims:
        assert single.scores[dim] == pytest.approx(batch.scores[dim], abs=1e-5)


@requires_torch
def test_training_forward_casts_bf16_pooled_output_to_head_dtype() -> None:
    import torch

    from forecheck.training.encoder_loop import _forward

    class _Backbone:
        def __call__(self, input_ids, attention_mask):
            class _Out:
                last_hidden_state = torch.ones(
                    (input_ids.shape[0], input_ids.shape[1], 4), dtype=torch.bfloat16
                )

            return _Out()

    head = torch.nn.Linear(4, 11)
    batch = {
        "input_ids": torch.ones((2, 3), dtype=torch.long),
        "attention_mask": torch.ones((2, 3)),
    }

    logits = _forward(torch, _Backbone(), head, batch, "mean")

    assert logits.shape == (2, 11)
    assert logits.dtype == torch.float32
