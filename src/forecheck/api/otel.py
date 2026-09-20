"""Optional OpenTelemetry hooks.

No-op unless ``FORECHECK_OTEL_ENABLED=true`` *and* the ``otel`` extra is importable.
Nothing else in this package imports ``opentelemetry`` directly, so it stays a soft
dependency end to end.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["instrument_app", "otel_available", "span"]


def otel_available() -> bool:
    try:
        import opentelemetry.instrumentation.fastapi  # type: ignore[import-not-found] # noqa: F401
    except ImportError:
        return False
    return True


def instrument_app(app: FastAPI, *, enabled: bool) -> None:
    if not enabled or not otel_available():
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


@contextmanager
def span(name: str, *, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return
    try:
        from opentelemetry import trace
    except ImportError:
        yield
        return
    tracer = trace.get_tracer("forecheck")
    with tracer.start_as_current_span(name):
        yield
