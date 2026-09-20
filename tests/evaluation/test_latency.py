from __future__ import annotations

from conftest import StubBackend, make_example

from forecheck.contracts import RiskDimension
from forecheck.evaluation.latency import measure_latency


def test_measure_latency_basic_shape() -> None:
    backend = StubBackend()
    examples = [make_example(f"e{i}") for i in range(5)]
    report = measure_latency(backend, examples)
    assert report.overall.n == 5
    assert report.overall.p50_ms >= 0
    assert report.overall.throughput_items_per_s > 0
    assert report.hardware.platform
    assert report.peak_traced_memory_bytes is not None
    assert len(report.by_num_dimensions) == 1
    assert report.by_num_dimensions[0].name == f"{len(list(RiskDimension))}_dimensions"


def test_measure_latency_empty_examples() -> None:
    backend = StubBackend()
    report = measure_latency(backend, [])
    assert report.overall.n == 0
    assert report.by_context_length_bucket == []
    assert report.by_num_dimensions == []


def test_measure_latency_multiple_dimension_subsets() -> None:
    backend = StubBackend()
    examples = [make_example("e1")]
    subsets = (None, [RiskDimension.FINANCIAL_COMMITMENT])
    report = measure_latency(backend, examples, dimension_subsets=subsets)
    names = {s.name for s in report.by_num_dimensions}
    assert f"{len(list(RiskDimension))}_dimensions" in names
    assert "1_dimensions" in names


def test_measure_latency_buckets_by_context_length() -> None:
    from forecheck.contracts import Observation, TrustLevel

    backend = StubBackend()
    short_example = make_example("short")
    long_example = make_example(
        "long",
        observations=(
            Observation(id="o1", source="web", trust=TrustLevel.UNTRUSTED, content="x" * 5000),
        ),
    )
    report = measure_latency(backend, [short_example, long_example])
    total_in_buckets = sum(s.stats.n for s in report.by_context_length_bucket)
    assert total_in_buckets == 2
