"""Calibration diagnostics: ECE, adaptive ECE, Brier score, NLL, reliability curves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "ReliabilityCurve",
    "adaptive_ece",
    "brier_score",
    "expected_calibration_error",
    "negative_log_likelihood",
    "reliability_curve",
]

_EPS = 1e-12


@dataclass(frozen=True, slots=True)
class ReliabilityCurve:
    bin_centers: NDArray[np.float64]
    accuracies: NDArray[np.float64]
    counts: NDArray[np.int_]


def _as_arrays(
    probabilities: NDArray[np.float64], labels: NDArray[np.int_]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    p = np.asarray(probabilities, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    if p.shape != y.shape:
        raise ValueError(f"shape mismatch: probabilities {p.shape} vs labels {y.shape}")
    return p, y


def expected_calibration_error(
    probabilities: NDArray[np.float64], labels: NDArray[np.int_], n_bins: int = 15
) -> float:
    """Equal-width-bin ECE: sum over bins of (weight * |accuracy - confidence|)."""
    p, y = _as_arrays(probabilities, labels)
    if p.size == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.clip(np.digitize(p, edges[1:-1], right=True), 0, n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        mask = bin_idx == b
        if not np.any(mask):
            continue
        weight = float(np.sum(mask)) / p.size
        accuracy = float(np.mean(y[mask]))
        confidence = float(np.mean(p[mask]))
        total += weight * abs(accuracy - confidence)
    return total


def adaptive_ece(
    probabilities: NDArray[np.float64], labels: NDArray[np.int_], n_bins: int = 15
) -> float:
    """Equal-mass-bin (quantile-binned) ECE."""
    p, y = _as_arrays(probabilities, labels)
    if p.size == 0:
        return 0.0
    order = np.argsort(p)
    p_sorted = p[order]
    y_sorted = y[order]
    bins = np.array_split(np.arange(p.size), min(n_bins, p.size))
    total = 0.0
    for idx in bins:
        if idx.size == 0:
            continue
        weight = float(idx.size) / p.size
        accuracy = float(np.mean(y_sorted[idx]))
        confidence = float(np.mean(p_sorted[idx]))
        total += weight * abs(accuracy - confidence)
    return total


def brier_score(probabilities: NDArray[np.float64], labels: NDArray[np.int_]) -> float:
    p, y = _as_arrays(probabilities, labels)
    if p.size == 0:
        return 0.0
    return float(np.mean((p - y) ** 2))


def negative_log_likelihood(probabilities: NDArray[np.float64], labels: NDArray[np.int_]) -> float:
    p, y = _as_arrays(probabilities, labels)
    if p.size == 0:
        return 0.0
    clipped = np.clip(p, _EPS, 1.0 - _EPS)
    return float(-np.mean(y * np.log(clipped) + (1.0 - y) * np.log(1.0 - clipped)))


def reliability_curve(
    probabilities: NDArray[np.float64], labels: NDArray[np.int_], n_bins: int = 15
) -> ReliabilityCurve:
    p, y = _as_arrays(probabilities, labels)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    accuracies = np.zeros(n_bins, dtype=np.float64)
    counts = np.zeros(n_bins, dtype=np.int_)
    if p.size:
        bin_idx = np.clip(np.digitize(p, edges[1:-1], right=True), 0, n_bins - 1)
        for b in range(n_bins):
            mask = bin_idx == b
            counts[b] = int(np.sum(mask))
            accuracies[b] = float(np.mean(y[mask])) if counts[b] else 0.0
    return ReliabilityCurve(bin_centers=centers, accuracies=accuracies, counts=counts)
