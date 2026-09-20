from __future__ import annotations

import numpy as np
import pytest

from forecheck.evaluation.selective import selective_risk_coverage


def test_perfect_separation_gives_zero_risk_everywhere() -> None:
    y_true = np.array([1, 1, 0, 0], dtype=np.int_)
    y_prob = np.array([0.9, 0.8, 0.2, 0.1], dtype=np.float64)
    result = selective_risk_coverage(y_true, y_prob)
    assert result.aurc == pytest.approx(0.0)
    for accuracy in result.selective_accuracy_at_coverage.values():
        assert accuracy == pytest.approx(1.0)


def test_selective_accuracy_improves_as_coverage_shrinks_with_wrong_low_confidence() -> None:
    y_true = np.array([1, 0, 1, 0], dtype=np.int_)
    y_prob = np.array([0.9, 0.1, 0.4, 0.6], dtype=np.float64)
    result = selective_risk_coverage(y_true, y_prob, coverage_levels=(0.5, 1.0))
    assert result.selective_accuracy_at_coverage[0.5] == pytest.approx(1.0)
    assert result.selective_accuracy_at_coverage[1.0] == pytest.approx(0.5)


def test_empty_input_returns_none_metrics() -> None:
    result = selective_risk_coverage(np.array([], dtype=np.int_), np.array([], dtype=np.float64))
    assert result.n == 0
    assert result.aurc is None
    assert all(v is None for v in result.selective_accuracy_at_coverage.values())


def test_custom_confidence_score_is_used_for_ordering() -> None:
    y_true = np.array([1, 0, 1, 0], dtype=np.int_)
    y_prob = np.array([0.6, 0.6, 0.4, 0.4], dtype=np.float64)
    default_result = selective_risk_coverage(y_true, y_prob, coverage_levels=(0.5,))
    inverted_confidence = np.array([0.1, 0.9, 0.1, 0.9], dtype=np.float64)
    inverted_result = selective_risk_coverage(
        y_true, y_prob, inverted_confidence, coverage_levels=(0.5,)
    )
    assert default_result.aurc != inverted_result.aurc


def test_n_matches_input_length() -> None:
    y_true = np.array([1, 0, 1], dtype=np.int_)
    y_prob = np.array([0.9, 0.1, 0.8], dtype=np.float64)
    result = selective_risk_coverage(y_true, y_prob)
    assert result.n == 3
