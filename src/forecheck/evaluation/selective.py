"""Selective risk / accuracy-vs-coverage metrics.

A calibrated classifier is more useful if it can also say "I don't know" on the
examples it would get wrong. These metrics measure that directly: sort examples by a
confidence score, keep only the most confident fraction (the "coverage"), and see how
accurate the kept predictions are. The default confidence score, ``|p - 0.5|``, treats
"close to the decision boundary" as "least confident"; callers with an external
abstention signal (e.g. a calibrator's predictive interval width) can supply their own.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["SelectiveResult", "selective_risk_coverage"]

DEFAULT_COVERAGE_LEVELS: tuple[float, ...] = (0.5, 0.7, 0.8, 0.9, 1.0)


class SelectiveResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    n: int
    aurc: float | None
    selective_accuracy_at_coverage: dict[float, float | None]


def selective_risk_coverage(
    y_true: NDArray[np.int_],
    y_prob: NDArray[np.float64],
    confidence: NDArray[np.float64] | None = None,
    *,
    threshold: float = 0.5,
    coverage_levels: Sequence[float] = DEFAULT_COVERAGE_LEVELS,
) -> SelectiveResult:
    """Risk-coverage curve, its area (AURC) and selective accuracy at fixed coverages.

    Predictions are thresholded at ``threshold`` to form the binary decision whose
    correctness defines "risk" (error rate) at each coverage level.
    """
    n = len(y_true)
    if n == 0:
        return SelectiveResult(
            n=0, aurc=None, selective_accuracy_at_coverage=dict.fromkeys(coverage_levels)
        )
    if confidence is None:
        confidence = np.abs(y_prob - 0.5)
    order = np.argsort(-confidence, kind="stable")
    y_true_sorted = y_true[order]
    y_pred_sorted = (y_prob[order] >= threshold).astype(np.int_)
    errors = (y_pred_sorted != y_true_sorted).astype(np.float64)
    cum_errors = np.cumsum(errors)
    ranks = np.arange(1, n + 1)
    risks = cum_errors / ranks
    coverages = ranks / n
    if n > 1:
        aurc = float(np.sum((risks[:-1] + risks[1:]) / 2 * np.diff(coverages)))
    else:
        aurc = float(risks[0])
    accuracy_at: dict[float, float | None] = {}
    for level in coverage_levels:
        k = min(max(1, round(level * n)), n)
        accuracy_at[level] = 1.0 - float(risks[k - 1])
    return SelectiveResult(n=n, aurc=aurc, selective_accuracy_at_coverage=accuracy_at)
