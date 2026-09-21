from __future__ import annotations

import importlib.util

import pytest

from forecheck.training.loss import masked_bce_with_logits, resolve_pos_weight
from tests.training.conftest import make_training_example

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")


def test_encoder_loss_functions_importable_without_torch() -> None:
    from forecheck.training import loss

    assert hasattr(loss, "masked_bce_with_logits")
    assert hasattr(loss, "resolve_pos_weight")


def test_resolve_pos_weight_returns_none_for_mode_none() -> None:
    from forecheck.contracts import RiskDimension

    result = resolve_pos_weight([], tuple(RiskDimension), "none")

    assert result is None


@requires_torch
def test_masked_bce_excludes_masked_cells_from_the_mean() -> None:
    import torch

    logits = torch.tensor([[5.0, 5.0], [-5.0, -5.0]])
    targets = torch.tensor([[1.0, 1.0], [0.0, 0.0]])
    mask = torch.tensor([[1.0, 0.0], [1.0, 0.0]])

    output = masked_bce_with_logits(logits, targets, mask)

    assert output.n_terms == 2
    assert float(output.loss) < 0.1


@requires_torch
def test_masked_bce_with_all_masked_cells_returns_zero_loss() -> None:
    import torch

    logits = torch.zeros((2, 3))
    targets = torch.zeros((2, 3))
    mask = torch.zeros((2, 3))

    output = masked_bce_with_logits(logits, targets, mask)

    assert output.n_terms == 0
    assert float(output.loss) == pytest.approx(0.0)


@requires_torch
def test_masked_bce_pos_weight_penalizes_missed_positives_more() -> None:
    import torch

    logits = torch.tensor([[-5.0]])
    targets = torch.tensor([[1.0]])
    mask = torch.tensor([[1.0]])

    unweighted = masked_bce_with_logits(logits, targets, mask)
    weighted = masked_bce_with_logits(logits, targets, mask, pos_weight=torch.tensor([4.0]))

    assert float(weighted.loss) > float(unweighted.loss)


@requires_torch
def test_resolve_pos_weight_balanced_matches_inverse_class_frequency() -> None:
    from forecheck.contracts import LabelValue, RiskDimension

    examples = [
        make_training_example(
            "ex-1", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.YES}
        ),
        make_training_example(
            "ex-2", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.NO}
        ),
        make_training_example(
            "ex-3", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.NO}
        ),
        make_training_example(
            "ex-4", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.NO}
        ),
    ]
    dimension_order = tuple(RiskDimension)
    weights = resolve_pos_weight(examples, dimension_order, "balanced")

    assert weights is not None
    index = dimension_order.index(RiskDimension.FINANCIAL_COMMITMENT)
    assert float(weights[index]) == pytest.approx(3.0)


@requires_torch
def test_resolve_pos_weight_defaults_to_one_with_no_positives() -> None:
    from forecheck.contracts import RiskDimension

    examples = [make_training_example("ex-1")]
    dimension_order = tuple(RiskDimension)
    weights = resolve_pos_weight(examples, dimension_order, "balanced")

    assert weights is not None
    index = dimension_order.index(RiskDimension.FINANCIAL_COMMITMENT)
    assert float(weights[index]) == pytest.approx(1.0)
