from __future__ import annotations

import pytest
from conftest import make_example, make_paraphrase_pair

from forecheck.contracts import ContrastiveAxis, LabelValue, RiskDimension, Transformation
from forecheck.evaluation.consistency import (
    counterfactual_sensitivity,
    invariance,
    pair_consistency,
)

DIM = RiskDimension.UNAUTHORIZED_SCOPE


def _authorization_pair() -> tuple[object, object, object]:
    base = make_example(
        "base",
        labels={**dict.fromkeys(RiskDimension, LabelValue.NO), DIM: LabelValue.NO},
    )
    transformed = make_example(
        "transformed",
        labels={**dict.fromkeys(RiskDimension, LabelValue.NO), DIM: LabelValue.YES},
        contrastive_pair_id="pair-1",
        transformation=Transformation(
            axis=ContrastiveAxis.PRINCIPAL_AUTHORIZATION,
            base_example_id="base",
            from_value="explicit",
            to_value="absent",
        ),
    )
    probabilities = {
        "base": {DIM: 0.1},
        "transformed": {DIM: 0.9},
    }
    return base, transformed, probabilities


def test_pair_consistency_correct_direction() -> None:
    base, transformed, probabilities = _authorization_pair()
    result = pair_consistency([base, transformed], probabilities)
    assert result.n_pairs == 1
    assert result.n_directional_pairs == 1
    assert result.fraction_correct_direction == 1.0
    assert result.mean_signed_delta is not None
    assert result.mean_signed_delta > 0


def test_pair_consistency_wrong_direction_is_detected() -> None:
    base, transformed, _ = _authorization_pair()
    probabilities = {"base": {DIM: 0.9}, "transformed": {DIM: 0.1}}
    result = pair_consistency([base, transformed], probabilities)
    assert result.fraction_correct_direction == 0.0
    assert result.mean_signed_delta is not None
    assert result.mean_signed_delta < 0


def test_pair_consistency_non_directional_label_delta_is_excluded() -> None:
    base = make_example("base")
    transformed = make_example(
        "transformed",
        contrastive_pair_id="pair-1",
        transformation=Transformation(
            axis=ContrastiveAxis.PRINCIPAL_AUTHORIZATION,
            base_example_id="base",
            from_value="explicit",
            to_value="absent",
        ),
    )
    probabilities = {"base": {DIM: 0.5}, "transformed": {DIM: 0.6}}
    result = pair_consistency([base, transformed], probabilities)
    assert result.n_pairs == 1
    assert result.n_directional_pairs == 0
    assert result.fraction_correct_direction is None


def test_pair_consistency_unresolvable_base_is_skipped() -> None:
    transformed = make_example(
        "transformed",
        contrastive_pair_id="pair-1",
        transformation=Transformation(
            axis=ContrastiveAxis.PRINCIPAL_AUTHORIZATION,
            base_example_id="does-not-exist",
            from_value="explicit",
            to_value="absent",
        ),
    )
    result = pair_consistency([transformed], {})
    assert result.n_pairs == 0


def test_counterfactual_sensitivity_measures_flipped_dimensions_only() -> None:
    base, transformed, probabilities = _authorization_pair()
    result = counterfactual_sensitivity([base, transformed], probabilities)
    assert result.n_observations == 1
    assert result.mean_abs_delta == 0.8


def test_invariance_detects_surface_paraphrase_movement() -> None:
    base, transformed = make_paraphrase_pair()
    probabilities = {
        base.example_id: dict.fromkeys(RiskDimension, 0.2),
        transformed.example_id: dict.fromkeys(RiskDimension, 0.4),
    }
    result = invariance([base, transformed], probabilities, tolerance=0.05)
    assert result.n_pairs == 1
    assert result.mean_abs_delta == pytest.approx(0.2)
    assert result.fraction_any_dimension_moved == 1.0


def test_invariance_no_movement_within_tolerance() -> None:
    base, transformed = make_paraphrase_pair()
    probabilities = {
        base.example_id: dict.fromkeys(RiskDimension, 0.2),
        transformed.example_id: dict.fromkeys(RiskDimension, 0.21),
    }
    result = invariance([base, transformed], probabilities, tolerance=0.05)
    assert result.fraction_any_dimension_moved == 0.0


def test_invariance_ignores_non_paraphrase_pairs() -> None:
    base = make_example("base")
    transformed = make_example(
        "transformed",
        contrastive_pair_id="pair-1",
        transformation=Transformation(
            axis=ContrastiveAxis.RESOURCE_SENSITIVITY,
            base_example_id="base",
            from_value="internal",
            to_value="restricted",
        ),
    )
    result = invariance([base, transformed], {})
    assert result.n_pairs == 0
    assert result.mean_abs_delta is None
    assert result.fraction_any_dimension_moved is None
