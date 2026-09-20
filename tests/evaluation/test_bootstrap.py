from __future__ import annotations

import numpy as np

from forecheck.evaluation.bootstrap import bootstrap_ci


def _mean_statistic(values: list[float]) -> object:
    def statistic(idx: np.ndarray) -> float | None:
        if len(idx) == 0:
            return None
        return float(np.mean(np.array(values)[idx]))

    return statistic


def test_bootstrap_ci_is_deterministic_for_fixed_seed() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    result_a = bootstrap_ci(_mean_statistic(values), len(values), seed=42, n_boot=200)
    result_b = bootstrap_ci(_mean_statistic(values), len(values), seed=42, n_boot=200)
    assert result_a == result_b


def test_bootstrap_ci_different_seeds_can_differ() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    result_a = bootstrap_ci(_mean_statistic(values), len(values), seed=1, n_boot=200)
    result_b = bootstrap_ci(_mean_statistic(values), len(values), seed=2, n_boot=200)
    assert result_a.point_estimate == result_b.point_estimate
    assert (result_a.lower, result_a.upper) != (result_b.lower, result_b.upper)


def test_bootstrap_ci_point_estimate_is_full_sample_statistic() -> None:
    values = [10.0, 20.0, 30.0]
    result = bootstrap_ci(_mean_statistic(values), len(values), seed=0, n_boot=50)
    assert result.point_estimate == 20.0


def test_bootstrap_ci_empty_input_returns_none_estimate() -> None:
    result = bootstrap_ci(_mean_statistic([]), 0, seed=0)
    assert result.point_estimate is None
    assert result.lower is None
    assert result.upper is None
    assert result.n_boot == 0


def test_bootstrap_ci_bounds_are_ordered() -> None:
    rng = np.random.default_rng(0)
    values = list(rng.normal(size=100))
    result = bootstrap_ci(_mean_statistic(values), len(values), seed=7, n_boot=500)
    assert result.lower is not None
    assert result.upper is not None
    assert result.lower <= result.point_estimate <= result.upper


def test_bootstrap_ci_stratified_never_mixes_groups() -> None:
    values = [0.0, 0.0, 0.0, 100.0, 100.0, 100.0]
    strata = ["a", "a", "a", "b", "b", "b"]

    def statistic(idx: np.ndarray) -> float | None:
        arr = np.array(values)[idx]
        return float(np.mean(arr))

    result = bootstrap_ci(statistic, len(values), seed=3, n_boot=300, strata=strata)
    assert result.point_estimate == 50.0
    assert result.lower is not None
    assert result.lower >= 0.0
    assert result.upper is not None
    assert result.upper <= 100.0
