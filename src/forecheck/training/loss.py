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

__all__ = ["LossOutput", "candidate_cross_entropy", "resolve_candidate_ids"]

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
