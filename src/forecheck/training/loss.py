"""Two-way candidate-token cross-entropy, matching :mod:`forecheck.inference.hf`.

Full-vocabulary cross-entropy at the answer position is the wrong objective here: it
would push probability mass onto the *literal* next token (one particular "yes"/"Yes"/
" yes" spelling, competing against the other ~150k vocabulary items including
irrelevant continuations), rather than onto the *decision* the two-way candidate set
encodes. A model can drive full-vocab CE down by learning surface-form preferences that
have nothing to do with risk, while barely moving the yes-vs-no log-odds ADR 0004
actually reads at serve time. Renormalizing over just the yes/no candidate ids and
computing CE there supervises exactly the quantity the backend scores with.

``LabelValue.NOT_APPLICABLE`` and ``LabelValue.UNDETERMINED`` cells carry no ground
truth (ADR-adjacent: see :mod:`forecheck.evaluation.metrics`) and are masked out of the
loss with weight zero rather than being coerced into a class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from forecheck.contracts import LabelValue, RiskDimension

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from forecheck.contracts import Example

__all__ = [
    "LossOutput",
    "MaskedBCEOutput",
    "candidate_cross_entropy",
    "masked_bce_with_logits",
    "resolve_candidate_ids",
    "resolve_pos_weight",
]

_MASKED_LABELS: frozenset[LabelValue] = frozenset(
    {LabelValue.NOT_APPLICABLE, LabelValue.UNDETERMINED}
)


def _require_torch() -> Any:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "forecheck.training.loss requires torch; install forecheck[train]"
        ) from exc
    return torch


@dataclass(frozen=True, slots=True)
class LossOutput:
    loss: Any
    n_terms: int
    per_dimension_loss: dict[RiskDimension, float]


def resolve_candidate_ids(
    tokenizer: Any,
    yes_surface_forms: Sequence[str],
    no_surface_forms: Sequence[str],
) -> tuple[frozenset[int], frozenset[int]]:
    """Resolve the yes/no candidate token ids using the exact serve-time resolver."""
    from forecheck.inference.hf import _resolve_candidate_ids

    yes_ids = _resolve_candidate_ids(tokenizer, tuple(yes_surface_forms), "yes")
    no_ids = _resolve_candidate_ids(tokenizer, tuple(no_surface_forms), "no")
    overlap = yes_ids & no_ids
    if overlap:
        raise ValueError(f"yes/no candidate token ids collide: {sorted(overlap)}")
    return frozenset(yes_ids), frozenset(no_ids)


def candidate_cross_entropy(
    logits: Any,
    dimensions: Sequence[RiskDimension],
    labels: Sequence[LabelValue],
    *,
    yes_ids: frozenset[int],
    no_ids: frozenset[int],
    dimension_weights: Mapping[RiskDimension, float] | None = None,
) -> LossOutput:
    """Weighted mean CE over the two-way candidate set, one term per answer position.

    ``logits`` is ``(n_positions, vocab_size)``: the model's output logits at each
    answer position, already gathered by the caller. ``dimensions``/``labels`` align
    with ``logits``'s first dimension. Masked rows (``NOT_APPLICABLE``/``UNDETERMINED``)
    get weight zero and do not affect the mean.
    """
    if not (len(dimensions) == len(labels) == logits.shape[0]):
        raise ValueError("logits, dimensions and labels must have matching length")
    torch = _require_torch()
    weights_cfg = dict(dimension_weights or {})
    device = logits.device

    yes_index = torch.tensor(sorted(yes_ids), dtype=torch.long, device=device)
    no_index = torch.tensor(sorted(no_ids), dtype=torch.long, device=device)
    yes_logp = torch.logsumexp(logits.index_select(-1, yes_index), dim=-1)
    no_logp = torch.logsumexp(logits.index_select(-1, no_index), dim=-1)
    log_z = torch.logsumexp(torch.stack([yes_logp, no_logp], dim=-1), dim=-1)
    logp_yes = yes_logp - log_z
    logp_no = no_logp - log_z

    target_is_yes = torch.tensor(
        [1.0 if label is LabelValue.YES else 0.0 for label in labels],
        dtype=logits.dtype,
        device=device,
    )
    per_term = -(target_is_yes * logp_yes + (1.0 - target_is_yes) * logp_no)
    weight = torch.tensor(
        [
            0.0 if label in _MASKED_LABELS else weights_cfg.get(dimension, 1.0)
            for dimension, label in zip(dimensions, labels, strict=True)
        ],
        dtype=logits.dtype,
        device=device,
    )
    denom = weight.sum()
    loss = (per_term * weight).sum() / denom if float(denom) > 0.0 else per_term.new_zeros(())

    per_dimension_loss: dict[RiskDimension, float] = {}
    for dimension, term, w in zip(
        dimensions, per_term.detach().tolist(), weight.detach().tolist(), strict=True
    ):
        if w > 0.0:
            per_dimension_loss[dimension] = float(term)
    n_terms = int((weight > 0).sum().item())
    return LossOutput(loss=loss, n_terms=n_terms, per_dimension_loss=per_dimension_loss)


@dataclass(frozen=True, slots=True)
class MaskedBCEOutput:
    loss: Any
    n_terms: int


def masked_bce_with_logits(
    logits: Any,
    targets: Any,
    mask: Any,
    *,
    pos_weight: Any | None = None,
) -> MaskedBCEOutput:
    """Mean BCE-with-logits over ``(batch, n_dimensions)``, excluding masked cells.

    ``mask`` is ``1.0`` for a ``YES``/``NO`` cell and ``0.0`` for
    ``NOT_APPLICABLE``/``UNDETERMINED``, matching :func:`candidate_cross_entropy`'s
    convention for the decoder loss. ``pos_weight`` is an optional per-dimension
    ``(n_dimensions,)`` tensor from :func:`resolve_pos_weight`.
    """
    torch = _require_torch()
    per_elem = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, targets, pos_weight=pos_weight, reduction="none"
    )
    masked = per_elem * mask
    denom = mask.sum()
    loss = masked.sum() / denom if float(denom) > 0.0 else masked.new_zeros(())
    n_terms = int(mask.sum().item())
    return MaskedBCEOutput(loss=loss, n_terms=n_terms)


def resolve_pos_weight(
    examples: Sequence[Example],
    dimension_order: Sequence[RiskDimension],
    mode: str,
) -> Any | None:
    """Compute a per-dimension positive-class weight for :func:`masked_bce_with_logits`.

    ``mode="none"`` returns ``None`` (no weighting). ``mode="balanced"`` returns
    ``n_negative / n_positive`` per dimension (the standard inverse-frequency
    correction for BCE), counting only ``YES``/``NO`` cells; a dimension with zero
    positives in the training split gets weight ``1.0`` rather than a division by zero.
    """
    if mode == "none":
        return None
    torch = _require_torch()
    weights: list[float] = []
    for dimension in dimension_order:
        n_pos = 0
        n_neg = 0
        for example in examples:
            label = example.labels.values[dimension]
            if label is LabelValue.YES:
                n_pos += 1
            elif label is LabelValue.NO:
                n_neg += 1
        weights.append(n_neg / n_pos if n_pos > 0 else 1.0)
    return torch.tensor(weights, dtype=torch.float32)
