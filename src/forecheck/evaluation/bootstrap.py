"""Seeded bootstrap confidence intervals.

Resampling is over *examples* (rows), never over per-row-per-dimension observations
independently, so a metric's CI reflects genuine dataset-level uncertainty rather than
pretending every cell is an independent draw. Optionally stratified: rows are grouped
by a caller-supplied key (typically ``family_id``) and each resample draws, with
replacement, exactly as many rows from each group as that group has, so no group's rows
are ever mixed into another group's draw and no group vanishes from a resample by
chance.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["BootstrapResult", "bootstrap_ci"]


class BootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    point_estimate: float | None
    lower: float | None
    upper: float | None
    n_boot: int
    seed: int
    alpha: float


def _grouped_indices(n: int, strata: Sequence[Hashable] | None) -> list[NDArray[np.intp]]:
    if strata is None:
        return [np.arange(n)]
    if len(strata) != n:
        raise ValueError("strata must have the same length as n")
    groups: dict[Hashable, list[int]] = {}
    for i, key in enumerate(strata):
        groups.setdefault(key, []).append(i)
    return [np.array(idx, dtype=np.intp) for idx in groups.values()]


def bootstrap_ci(
    values_fn: Callable[[NDArray[np.intp]], float | None],
    n: int,
    seed: int,
    *,
    n_boot: int = 1000,
    alpha: float = 0.05,
    strata: Sequence[Hashable] | None = None,
) -> BootstrapResult:
    """Bootstrap a scalar statistic computed by ``values_fn`` over row indices ``[0, n)``.

    ``values_fn`` receives an array of (possibly repeated) row indices for one resample
    and returns the statistic on that resample, or ``None`` if it is undefined for that
    resample (e.g. no positives at all). A fixed ``seed`` yields an identical result on
    every call.
    """
    point_estimate = values_fn(np.arange(n, dtype=np.intp)) if n > 0 else None
    if n == 0:
        return BootstrapResult(
            point_estimate=point_estimate, lower=None, upper=None, n_boot=0, seed=seed, alpha=alpha
        )
    rng = np.random.default_rng(seed)
    groups = _grouped_indices(n, strata)
    samples: list[float] = []
    for _ in range(n_boot):
        parts = [rng.choice(idx, size=len(idx), replace=True) for idx in groups]
        resample_idx = np.concatenate(parts) if parts else np.array([], dtype=np.intp)
        value = values_fn(resample_idx)
        if value is not None:
            samples.append(value)
    if not samples:
        return BootstrapResult(
            point_estimate=point_estimate, lower=None, upper=None, n_boot=0, seed=seed, alpha=alpha
        )
    arr = np.array(samples, dtype=np.float64)
    lower = float(np.quantile(arr, alpha / 2))
    upper = float(np.quantile(arr, 1 - alpha / 2))
    return BootstrapResult(
        point_estimate=point_estimate,
        lower=lower,
        upper=upper,
        n_boot=len(samples),
        seed=seed,
        alpha=alpha,
    )
