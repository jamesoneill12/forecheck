from __future__ import annotations

import importlib.util

import pytest

from forecheck.training.loss import resolve_candidate_ids
from tests.training.conftest import FakeTokenizer

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")


def test_loss_module_imports_without_torch() -> None:
    from forecheck.training import loss

    assert hasattr(loss, "candidate_cross_entropy")
    assert hasattr(loss, "LossOutput")


def test_require_torch_raises_helpful_error_when_missing() -> None:
    if HAS_TORCH:
        pytest.skip("torch is installed; this exercises the missing-torch error path only")
    from forecheck.training import loss

    with pytest.raises(ImportError, match=r"forecheck\[train\]"):
        loss._require_torch()


def test_resolve_candidate_ids_uses_the_serve_time_resolver(fake_tokenizer: FakeTokenizer) -> None:
    yes_ids, no_ids = resolve_candidate_ids(
        fake_tokenizer, ("yes", "Yes", "YES"), ("no", "No", "NO")
    )

    assert yes_ids.isdisjoint(no_ids)
    assert len(yes_ids) == 3
    assert len(no_ids) == 3


def test_resolve_candidate_ids_rejects_overlapping_forms(fake_tokenizer: FakeTokenizer) -> None:
    with pytest.raises(ValueError, match="collide"):
        resolve_candidate_ids(fake_tokenizer, ("yes",), ("yes",))


@requires_torch
def test_candidate_cross_entropy_masks_not_applicable_and_undetermined() -> None:
    import torch

    from forecheck.contracts import LabelValue, RiskDimension
    from forecheck.training.loss import candidate_cross_entropy

    vocab = 10
    logits = torch.zeros((3, vocab))
    logits[:, 1] = 5.0  # a "yes"-side id
    logits[:, 2] = -5.0  # a "no"-side id
    dimensions = [
        RiskDimension.FINANCIAL_COMMITMENT,
        RiskDimension.UNAUTHORIZED_SCOPE,
        RiskDimension.INSUFFICIENT_CONTEXT,
    ]
    labels = [LabelValue.YES, LabelValue.NO, LabelValue.NOT_APPLICABLE]

    output = candidate_cross_entropy(
        logits, dimensions, labels, yes_ids=frozenset({1}), no_ids=frozenset({2})
    )

    assert output.n_terms == 2
    assert RiskDimension.INSUFFICIENT_CONTEXT not in output.per_dimension_loss
    assert float(output.loss) >= 0.0


@requires_torch
def test_candidate_cross_entropy_applies_dimension_weights() -> None:
    import torch

    from forecheck.contracts import LabelValue, RiskDimension
    from forecheck.training.loss import candidate_cross_entropy

    logits = torch.zeros((2, 4))
    dimensions = [RiskDimension.FINANCIAL_COMMITMENT, RiskDimension.UNAUTHORIZED_SCOPE]
    labels = [LabelValue.YES, LabelValue.YES]

    unweighted = candidate_cross_entropy(
        logits, dimensions, labels, yes_ids=frozenset({0}), no_ids=frozenset({1})
    )
    weighted = candidate_cross_entropy(
        logits,
        dimensions,
        labels,
        yes_ids=frozenset({0}),
        no_ids=frozenset({1}),
        dimension_weights={RiskDimension.FINANCIAL_COMMITMENT: 0.0},
    )

    assert float(weighted.loss) != float(unweighted.loss)
