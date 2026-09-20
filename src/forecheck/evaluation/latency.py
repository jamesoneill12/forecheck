"""Latency, throughput and memory harness for a :class:`ClassifierBackend`.

No dependency on ``psutil``: peak resident memory comes from :mod:`resource` where
available (``ru_maxrss``, a process-lifetime high-water mark, not scoped to this
benchmark alone) and peak Python-heap growth during the benchmark comes from
:mod:`tracemalloc`, which is portable and scoped to exactly the timed region.
"""

from __future__ import annotations

import os
import platform
import time
import tracemalloc
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from forecheck.contracts import RiskDimension
from forecheck.evaluation.slices import rendered_context_length, rendered_context_length_bucket

if TYPE_CHECKING:
    from forecheck.contracts import Example
    from forecheck.inference.base import ClassifierBackend

__all__ = [
    "HardwareInfo",
    "LatencyReport",
    "LatencySliceResult",
    "LatencyStats",
    "measure_latency",
]


class HardwareInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    platform: str
    processor: str
    cpu_count: int | None
    torch_device: str | None


class LatencyStats(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    n: int
    p50_ms: float
    p90_ms: float
    p99_ms: float
    mean_ms: float
    throughput_items_per_s: float


class LatencySliceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    stats: LatencyStats


class LatencyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    overall: LatencyStats
    by_context_length_bucket: list[LatencySliceResult]
    by_num_dimensions: list[LatencySliceResult]
    peak_rss_bytes: int | None
    peak_traced_memory_bytes: int | None
    hardware: HardwareInfo


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def _stats_from_durations(durations_s: Sequence[float]) -> LatencyStats:
    if not durations_s:
        return LatencyStats(
            n=0, p50_ms=0.0, p90_ms=0.0, p99_ms=0.0, mean_ms=0.0, throughput_items_per_s=0.0
        )
    sorted_ms = sorted(d * 1000 for d in durations_s)
    total_s = sum(durations_s)
    throughput = len(durations_s) / total_s if total_s > 0 else float("inf")
    return LatencyStats(
        n=len(durations_s),
        p50_ms=_percentile(sorted_ms, 0.5),
        p90_ms=_percentile(sorted_ms, 0.9),
        p99_ms=_percentile(sorted_ms, 0.99),
        mean_ms=sum(sorted_ms) / len(sorted_ms),
        throughput_items_per_s=throughput,
    )


def _torch_device() -> str | None:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return None
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _hardware_info() -> HardwareInfo:
    return HardwareInfo(
        platform=platform.platform(),
        processor=platform.processor() or platform.machine(),
        cpu_count=os.cpu_count(),
        torch_device=_torch_device(),
    )


def _peak_rss_bytes() -> int | None:
    try:
        import resource
    except ImportError:
        return None
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return int(max_rss)
    return int(max_rss) * 1024


def _context_length_bucket(example: Example) -> str:
    return rendered_context_length_bucket(rendered_context_length(example))


def measure_latency(
    backend: ClassifierBackend,
    examples: Sequence[Example],
    *,
    dimension_subsets: Sequence[Sequence[RiskDimension] | None] = (None,),
) -> LatencyReport:
    """Time ``backend.score`` over ``examples``, once per entry in ``dimension_subsets``.

    The first subset in ``dimension_subsets`` (conventionally ``None``, meaning "all
    dimensions") is also used to build ``overall`` and the context-length-bucket
    breakdown; every subset contributes one entry to ``by_num_dimensions``.
    """
    if not examples:
        empty = _stats_from_durations([])
        return LatencyReport(
            overall=empty,
            by_context_length_bucket=[],
            by_num_dimensions=[],
            peak_rss_bytes=_peak_rss_bytes(),
            peak_traced_memory_bytes=None,
            hardware=_hardware_info(),
        )
    tracemalloc.start()
    primary_durations: list[float] = []
    bucket_durations: dict[str, list[float]] = {}
    by_num_dimensions: list[LatencySliceResult] = []
    for subset_idx, dimensions in enumerate(dimension_subsets):
        durations: list[float] = []
        for example in examples:
            start = time.perf_counter()
            backend.score(example.context, dimensions)
            durations.append(time.perf_counter() - start)
            if subset_idx == 0:
                bucket = _context_length_bucket(example)
                bucket_durations.setdefault(bucket, []).append(durations[-1])
        if subset_idx == 0:
            primary_durations = durations
        n_dims = len(dimensions) if dimensions is not None else len(list(RiskDimension))
        by_num_dimensions.append(
            LatencySliceResult(name=f"{n_dims}_dimensions", stats=_stats_from_durations(durations))
        )
    _, peak_traced = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    by_bucket = [
        LatencySliceResult(name=bucket, stats=_stats_from_durations(durations))
        for bucket, durations in sorted(bucket_durations.items())
    ]
    return LatencyReport(
        overall=_stats_from_durations(primary_durations),
        by_context_length_bucket=by_bucket,
        by_num_dimensions=by_num_dimensions,
        peak_rss_bytes=_peak_rss_bytes(),
        peak_traced_memory_bytes=peak_traced,
        hardware=_hardware_info(),
    )
