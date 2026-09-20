"""Synchronous and asynchronous HTTP clients for the forecheck service.

Both clients speak the fixed route surface (``/v1/classify``, ``/v1/classify/batch``,
``/v1/policies/evaluate``, ``/v1/policies``, ``/health/live``, ``/health/ready``,
``/version``) and never import :mod:`forecheck.api`. Request bodies are never logged.
Retries apply only to ``ErrorBody.retryable`` 5xx responses or connection failures,
never to a 4xx response, and use jittered exponential backoff.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, Any, Final

import httpx
from pydantic import ValidationError

from forecheck.contracts import (
    ActionContext,
    BatchClassifyRequest,
    BatchClassifyResponse,
    ClassifyRequest,
    ClassifyResponse,
    ErrorCode,
    ErrorResponse,
    PolicyDecision,
    PolicyEvaluateRequest,
)

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ["AsyncForecheckClient", "ForecheckClient", "ForecheckClientError"]

REQUEST_ID_HEADER: Final[str] = "X-Request-Id"
POLICY_BUNDLE_HEADER: Final[str] = "X-Forecheck-Policy-Bundle"

_PATH_CLASSIFY: Final[str] = "/v1/classify"
_PATH_CLASSIFY_BATCH: Final[str] = "/v1/classify/batch"
_PATH_POLICIES_EVALUATE: Final[str] = "/v1/policies/evaluate"
_PATH_POLICIES: Final[str] = "/v1/policies"
_PATH_HEALTH_LIVE: Final[str] = "/health/live"
_PATH_HEALTH_READY: Final[str] = "/health/ready"
_PATH_VERSION: Final[str] = "/version"

_BACKOFF_BASE_S: Final[float] = 0.05
_BACKOFF_MAX_S: Final[float] = 1.0


class ForecheckClientError(Exception):
    """Raised when the forecheck service returns an error envelope, or a transport
    failure survives all retries."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status: int,
        request_id: str | None = None,
    ) -> None:
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.status = status
        self.request_id = request_id


def _backoff_delay(attempt: int) -> float:
    delay: float = min(_BACKOFF_MAX_S, _BACKOFF_BASE_S * (2.0**attempt))
    jitter: float = random.uniform(0.0, delay * 0.25)  # noqa: S311
    return delay + jitter


def _headers(token: str | None, request_id: str | None, bundle: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = request_id
    if bundle is not None:
        headers[POLICY_BUNDLE_HEADER] = bundle
    return headers


def _parse_error(response: httpx.Response) -> ForecheckClientError:
    request_id = response.headers.get(REQUEST_ID_HEADER)
    try:
        body = ErrorResponse.model_validate(response.json())
    except (ValueError, ValidationError):
        return ForecheckClientError(
            ErrorCode.INTERNAL_ERROR,
            f"unexpected error response (status {response.status_code}): {response.text[:512]}",
            status=response.status_code,
            request_id=request_id,
        )
    return ForecheckClientError(
        body.error.code,
        body.error.message,
        status=response.status_code,
        request_id=body.request_id or request_id,
    )


def _is_retryable(response: httpx.Response) -> bool:
    if 400 <= response.status_code < 500:
        return False
    try:
        body = ErrorResponse.model_validate(response.json())
    except (ValueError, ValidationError):
        return response.status_code >= 500
    return body.error.retryable


class ForecheckClient:
    """Synchronous client. Not thread-safe across concurrent requests sharing state
    beyond the underlying ``httpx.Client``, which is itself safe for concurrent use."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        *,
        timeout_s: float = 5.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token = token
        self._retries = retries
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ForecheckClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        request_id: str | None = None,
        bundle: str | None = None,
    ) -> httpx.Response:
        headers = _headers(self._token, request_id, bundle)
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.request(method, path, json=json_body, headers=headers)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt >= self._retries:
                    raise ForecheckClientError(
                        ErrorCode.BACKEND_ERROR,
                        f"transport error calling {path}: {exc}",
                        status=0,
                        request_id=request_id,
                    ) from exc
                time.sleep(_backoff_delay(attempt))
                continue
            if response.status_code < 300:
                return response
            if attempt < self._retries and _is_retryable(response):
                time.sleep(_backoff_delay(attempt))
                continue
            raise _parse_error(response)
        if last_error is not None:  # pragma: no cover - defensive, unreachable
            raise ForecheckClientError(
                ErrorCode.BACKEND_ERROR, str(last_error), status=0, request_id=request_id
            )
        raise AssertionError("unreachable")  # pragma: no cover

    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        response = self._request(
            "POST",
            _PATH_CLASSIFY,
            json_body=request.model_dump(mode="json"),
            request_id=request.request_id,
        )
        return ClassifyResponse.model_validate(response.json())

    def classify_batch(self, request: BatchClassifyRequest) -> BatchClassifyResponse:
        response = self._request(
            "POST", _PATH_CLASSIFY_BATCH, json_body=request.model_dump(mode="json")
        )
        return BatchClassifyResponse.model_validate(response.json())

    def evaluate(
        self, request: PolicyEvaluateRequest, *, bundle: str | None = None
    ) -> PolicyDecision:
        response = self._request(
            "POST",
            _PATH_POLICIES_EVALUATE,
            json_body=request.model_dump(mode="json"),
            request_id=request.request_id,
            bundle=bundle,
        )
        return PolicyDecision.model_validate(response.json())

    def classify_and_evaluate(
        self,
        context: ActionContext,
        *,
        bundle: str | None = None,
        request_id: str | None = None,
    ) -> PolicyDecision:
        request = PolicyEvaluateRequest(request_id=request_id, context=context)
        return self.evaluate(request, bundle=bundle)

    def list_policies(self) -> list[dict[str, Any]]:
        response = self._request("GET", _PATH_POLICIES)
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    def ready(self) -> bool:
        try:
            response = self._client.get(_PATH_HEALTH_READY)
        except httpx.TransportError:
            return False
        return response.status_code < 300

    def live(self) -> bool:
        try:
            response = self._client.get(_PATH_HEALTH_LIVE)
        except httpx.TransportError:
            return False
        return response.status_code < 300

    def version(self) -> dict[str, Any]:
        response = self._request("GET", _PATH_VERSION)
        payload: dict[str, Any] = response.json()
        return payload


class AsyncForecheckClient:
    """Asynchronous mirror of :class:`ForecheckClient`."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        *,
        timeout_s: float = 5.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._retries = retries
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncForecheckClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        request_id: str | None = None,
        bundle: str | None = None,
    ) -> httpx.Response:
        headers = _headers(self._token, request_id, bundle)
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(method, path, json=json_body, headers=headers)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt >= self._retries:
                    raise ForecheckClientError(
                        ErrorCode.BACKEND_ERROR,
                        f"transport error calling {path}: {exc}",
                        status=0,
                        request_id=request_id,
                    ) from exc
                await asyncio.sleep(_backoff_delay(attempt))
                continue
            if response.status_code < 300:
                return response
            if attempt < self._retries and _is_retryable(response):
                await asyncio.sleep(_backoff_delay(attempt))
                continue
            raise _parse_error(response)
        if last_error is not None:  # pragma: no cover - defensive, unreachable
            raise ForecheckClientError(
                ErrorCode.BACKEND_ERROR, str(last_error), status=0, request_id=request_id
            )
        raise AssertionError("unreachable")  # pragma: no cover

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        response = await self._request(
            "POST",
            _PATH_CLASSIFY,
            json_body=request.model_dump(mode="json"),
            request_id=request.request_id,
        )
        return ClassifyResponse.model_validate(response.json())

    async def classify_batch(self, request: BatchClassifyRequest) -> BatchClassifyResponse:
        response = await self._request(
            "POST", _PATH_CLASSIFY_BATCH, json_body=request.model_dump(mode="json")
        )
        return BatchClassifyResponse.model_validate(response.json())

    async def evaluate(
        self, request: PolicyEvaluateRequest, *, bundle: str | None = None
    ) -> PolicyDecision:
        response = await self._request(
            "POST",
            _PATH_POLICIES_EVALUATE,
            json_body=request.model_dump(mode="json"),
            request_id=request.request_id,
            bundle=bundle,
        )
        return PolicyDecision.model_validate(response.json())

    async def classify_and_evaluate(
        self,
        context: ActionContext,
        *,
        bundle: str | None = None,
        request_id: str | None = None,
    ) -> PolicyDecision:
        request = PolicyEvaluateRequest(request_id=request_id, context=context)
        return await self.evaluate(request, bundle=bundle)

    async def list_policies(self) -> list[dict[str, Any]]:
        response = await self._request("GET", _PATH_POLICIES)
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def ready(self) -> bool:
        try:
            response = await self._client.get(_PATH_HEALTH_READY)
        except httpx.TransportError:
            return False
        return response.status_code < 300

    async def live(self) -> bool:
        try:
            response = await self._client.get(_PATH_HEALTH_LIVE)
        except httpx.TransportError:
            return False
        return response.status_code < 300

    async def version(self) -> dict[str, Any]:
        response = await self._request("GET", _PATH_VERSION)
        payload: dict[str, Any] = response.json()
        return payload
