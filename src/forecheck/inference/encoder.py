"""Encoder-classifier backend: a pooled-embedding backbone plus a linear head.

Scores a dimension by encoding :func:`serialize_context`'s rendered text with an
encoder backbone (e.g. ModernBERT-large or granite-embedding-english-r2), pooling the
final hidden states, and reading one logit per :class:`~forecheck.contracts.RiskDimension`
off a small linear head trained by :mod:`forecheck.training.encoder_loop`. Unlike
:class:`forecheck.inference.hf.HFBackend`, there is no question and no chat template --
the encoder never sees anything beyond the serialized context, so its raw score is a
direct per-dimension logit rather than a candidate-token log-odds. Both are log-odds
scale and both plug into :class:`~forecheck.inference.base.ClassifierBackend` unchanged.

All ``torch``/``transformers``/``safetensors`` imports are deferred to call time so this
module -- and therefore ``forecheck.inference`` -- imports cleanly without the ``train``
extra installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from forecheck.contracts import LABEL_SCHEMA_VERSION, ModelInfo, RiskDimension
from forecheck.inference.base import BackendCapabilities, BaseBackend, RawScores
from forecheck.inference.serialization import serialize_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forecheck.contracts import ActionContext

__all__ = [
    "HEAD_CONFIG_FILE",
    "HEAD_WEIGHTS_FILE",
    "EncoderBackend",
    "EncoderBackendConfig",
    "Pooling",
]

Pooling = Literal["mean", "cls"]

HEAD_CONFIG_FILE = "head_config.json"
HEAD_WEIGHTS_FILE = "head.safetensors"
BACKBONE_DIR = "backbone"

_TORCH_INSTALL_HINT = (
    "the encoder backend requires torch, transformers and safetensors; "
    "install with pip install 'forecheck[train]'"
)


def _require_torch() -> Any:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(_TORCH_INSTALL_HINT) from exc
    return torch


@dataclass(frozen=True, slots=True)
class EncoderBackendConfig:
    model_id: str
    run_dir: Path
    pooling: Pooling = "mean"
    max_tokens: int = 2048
    device: str | None = None
    dtype: str | None = None
    batch_size: int = 32
    strip_identity: bool = False


def _auto_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _resolve_dtype(torch: Any, dtype_name: str | None, device: str) -> Any:
    if dtype_name is not None:
        short_names = {"bf16": "bfloat16", "fp16": "float16", "fp32": "float32"}
        return getattr(torch, short_names.get(dtype_name, dtype_name))
    return torch.float32 if device == "cpu" else torch.bfloat16


def pool_hidden_states(
    torch: Any, last_hidden_state: Any, attention_mask: Any, pooling: Pooling
) -> Any:
    """Reduce ``(batch, seq, hidden)`` states to ``(batch, hidden)`` for one dimension head."""
    if pooling == "cls":
        return last_hidden_state[:, 0, :]
    mask = attention_mask.unsqueeze(-1).to(last_hidden_state.dtype)
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def head_checkpoint_dir(run_dir: Path) -> Path:
    return run_dir / "checkpoints" / "best"


class EncoderBackend(BaseBackend):
    def __init__(self, config: EncoderBackendConfig) -> None:
        self._config = config
        self._backbone: Any = None
        self._tokenizer: Any = None
        self._device: str | None = None
        self._head_weight: Any = None
        self._head_bias: Any = None
        self._dimension_order: tuple[RiskDimension, ...] | None = None
        self._serialization_contract_hash: str | None = None

    def _ensure_loaded(self) -> None:
        if self._backbone is not None:
            return
        torch = _require_torch()
        from safetensors.torch import load_file

        checkpoint_dir = head_checkpoint_dir(self._config.run_dir)
        head_config = json.loads((checkpoint_dir / HEAD_CONFIG_FILE).read_text(encoding="utf-8"))
        self._dimension_order = tuple(RiskDimension(d) for d in head_config["dimension_order"])
        self._serialization_contract_hash = head_config["serialization_contract_hash"]

        device = self._config.device or _auto_device(torch)
        dtype = _resolve_dtype(torch, self._config.dtype, device)

        from transformers import AutoModel, AutoTokenizer

        backbone_dir = checkpoint_dir / BACKBONE_DIR
        backbone = AutoModel.from_pretrained(str(backbone_dir), torch_dtype=dtype)
        backbone.to(device)
        backbone.eval()
        tokenizer = AutoTokenizer.from_pretrained(str(backbone_dir))

        head_state = load_file(str(checkpoint_dir / HEAD_WEIGHTS_FILE))
        self._head_weight = head_state["weight"].to(device=device, dtype=dtype)
        self._head_bias = head_state["bias"].to(device=device, dtype=dtype)

        self._backbone = backbone
        self._tokenizer = tokenizer
        self._device = device

    def warmup(self) -> None:
        self._ensure_loaded()

    def close(self) -> None:
        if self._backbone is not None:
            torch = _require_torch()
            self._backbone = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    @property
    def model_info(self) -> ModelInfo:
        contract_hash = self._serialization_contract_hash
        if contract_hash is None:
            from forecheck.inference.prompt import serialization_contract_hash

            contract_hash = serialization_contract_hash()
        return ModelInfo(
            backend="encoder",
            model_id=self._config.model_id,
            revision=None,
            base_model=self._config.model_id,
            adapter_id=str(self._config.run_dir),
            prompt_contract_hash=contract_hash,
            label_schema_version=LABEL_SCHEMA_VERSION,
            quantization=None,
        )

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_batching=True,
            supports_shared_prefill=False,
            max_prompt_tokens=self._config.max_tokens,
            device=self._device or self._config.device or "cpu",
            deterministic=True,
        )

    def _dims_or_all(self, dimensions: Sequence[RiskDimension] | None) -> list[RiskDimension]:
        return list(dimensions) if dimensions is not None else list(RiskDimension)

    def _logits_for_texts(self, torch: Any, texts: list[str]) -> tuple[Any, list[int]]:
        encoded = self._tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=self._config.max_tokens,
        )
        encoded = {k: v.to(self._device) for k, v in encoded.items()}
        with torch.no_grad():
            outputs = self._backbone(**encoded)
            pooled = pool_hidden_states(
                torch, outputs.last_hidden_state, encoded["attention_mask"], self._config.pooling
            )
            logits = pooled.to(self._head_weight.dtype) @ self._head_weight.T + self._head_bias
        prompt_tokens = encoded["attention_mask"].sum(dim=1).tolist()
        return logits, [int(t) for t in prompt_tokens]

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        return self.score_batch([context], dimensions)[0]

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]:
        self._ensure_loaded()
        torch = _require_torch()
        assert self._dimension_order is not None
        dims = self._dims_or_all(dimensions)
        dim_index = {d: i for i, d in enumerate(self._dimension_order)}

        rendered = [
            serialize_context(
                c, max_tokens=self._config.max_tokens, strip_identity=self._config.strip_identity
            )
            for c in contexts
        ]
        results: list[RawScores | None] = [None] * len(contexts)
        for start in range(0, len(contexts), self._config.batch_size):
            end = min(start + self._config.batch_size, len(contexts))
            texts = [rendered[i].text for i in range(start, end)]
            logits, prompt_tokens = self._logits_for_texts(torch, texts)
            for offset, i in enumerate(range(start, end)):
                row = logits[offset]
                scores = {dim: float(row[dim_index[dim]]) for dim in dims}
                results[i] = RawScores(
                    scores=scores,
                    truncation=rendered[i].truncation,
                    prompt_tokens=prompt_tokens[offset],
                )
        return [r for r in results if r is not None]
