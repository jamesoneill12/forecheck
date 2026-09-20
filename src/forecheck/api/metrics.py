"""Prometheus metrics exposed at ``GET /metrics``.

``tenant`` labels are bounded by hashing the tenant id to a fixed-width hex prefix
rather than using it verbatim: tenant ids are caller-controlled and otherwise
unbounded cardinality, and this keeps them out of metric label values entirely while
still letting a per-tenant rate be graphed.
"""

from __future__ import annotations

import hashlib

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "ABSTENTIONS_TOTAL",
    "DECISIONS_TOTAL",
    "DIMENSION_PROBABILITY",
    "MODEL_READY",
    "REGISTRY",
    "REQUESTS_TOTAL",
    "REQUEST_LATENCY_SECONDS",
    "render",
    "tenant_label",
]

REGISTRY = CollectorRegistry()

REQUESTS_TOTAL = Counter(
    "forecheck_requests_total",
    "Total HTTP requests handled.",
    ["route", "status", "tenant"],
    registry=REGISTRY,
)

REQUEST_LATENCY_SECONDS = Histogram(
    "forecheck_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["route"],
    registry=REGISTRY,
)

DIMENSION_PROBABILITY = Histogram(
    "forecheck_dimension_probability",
    "Calibrated probability emitted per risk dimension.",
    ["dimension"],
    buckets=(0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
    registry=REGISTRY,
)

DECISIONS_TOTAL = Counter(
    "forecheck_decisions_total",
    "Policy decisions returned, by decision and bundle.",
    ["decision", "bundle"],
    registry=REGISTRY,
)

MODEL_READY = Gauge(
    "forecheck_model_ready",
    "1 once the backend has loaded and warmed up, else 0.",
    registry=REGISTRY,
)

ABSTENTIONS_TOTAL = Counter(
    "forecheck_abstentions_total",
    "Response-level abstentions, by reason.",
    ["reason"],
    registry=REGISTRY,
)


def tenant_label(tenant_id: str | None) -> str:
    if tenant_id is None:
        return "none"
    return hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:12]


def render() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
