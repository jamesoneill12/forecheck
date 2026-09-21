"""The ``create_app`` factory: assembles middleware, routers, exception handlers,
lifespan (backend load + warm-up + graceful shutdown) and OTel instrumentation.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Response

from forecheck.api import metrics, otel
from forecheck.api.deps import build_app_state, run_warmup, shutdown_app_state
from forecheck.api.errors import install_exception_handlers
from forecheck.api.routes import classify, feedback, health, policies
from forecheck.api.settings import Settings
from forecheck.version import __version__

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ["create_app"]


def _configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RequestSizeLimitMiddleware:
    """Rejects an oversized body with ``REQUEST_TOO_LARGE`` before any JSON parsing.

    Uses ``Content-Length`` when present; otherwise counts bytes as the ASGI server
    delivers them and aborts as soon as the running total exceeds the limit, so an
    attacker cannot force the full body into memory first.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = None
            if declared is not None and declared > self._max_bytes:
                await self._reject(send)
                return
            await self._app(scope, receive, send)
            return

        buffered: list[Message] = []
        seen = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self._max_bytes:
                    await self._reject(send)
                    return
            if message["type"] != "http.request" or not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return await receive()

        await self._app(scope, replay_receive, send)

    async def _reject(self, send: Send) -> None:
        from forecheck.contracts import ErrorBody, ErrorCode, ErrorResponse
        from forecheck.contracts.errors import HTTP_STATUS_FOR_CODE

        payload = ErrorResponse(
            error=ErrorBody(
                code=ErrorCode.REQUEST_TOO_LARGE,
                message=f"request body exceeds {self._max_bytes} bytes",
                retryable=False,
            )
        ).model_dump_json()
        await send(
            {
                "type": "http.response.start",
                "status": HTTP_STATUS_FOR_CODE[ErrorCode.REQUEST_TOO_LARGE],
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": payload.encode("utf-8")})


def _header(scope: Scope, name: bytes) -> str | None:
    headers: list[tuple[bytes, bytes]] = scope.get("headers") or []
    for key, value in headers:
        if key == name:
            return value.decode("latin-1")
    return None


class RequestContextMiddleware:
    """Assigns a request id, echoes it on the response, and records the request-count
    and latency metrics with a bounded tenant label once the route has run."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _header(scope, b"x-request-id") or str(uuid.uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        start = time.perf_counter()
        status_holder: dict[str, int] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, send_wrapper)

        elapsed = time.perf_counter() - start
        status = status_holder.get("status", 500)
        route = scope.get("path", "unknown")
        tenant = metrics.tenant_label(state.get("tenant_id"))
        metrics.REQUESTS_TOTAL.labels(route=route, status=str(status), tenant=tenant).inc()
        metrics.REQUEST_LATENCY_SECONDS.labels(route=route).observe(elapsed)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    _configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        state = await build_app_state(resolved_settings)
        app.state.forecheck = state
        metrics.MODEL_READY.set(0)
        try:
            await run_warmup(state)
            state.ready = True
            metrics.MODEL_READY.set(1)
            yield
        finally:
            metrics.MODEL_READY.set(0)
            state.ready = False
            await shutdown_app_state(state)

    app = FastAPI(
        title="forecheck",
        description="A calibrated pre-execution risk model for AI-agent actions.",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=resolved_settings.max_request_bytes)

    install_exception_handlers(app)

    app.include_router(classify.router)
    app.include_router(policies.router)
    app.include_router(feedback.router)
    app.include_router(health.router)

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        """Prometheus text exposition of every forecheck_* metric."""
        payload, content_type = metrics.render()
        return Response(content=payload, media_type=content_type)

    otel.instrument_app(app, enabled=resolved_settings.otel_enabled)

    return app
