from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from forecheck.contracts import (
    CalibrationInfo,
    ClassifyRequest,
    ClassifyResponse,
    Decision,
    ErrorBody,
    ErrorCode,
    ErrorResponse,
    FeedbackOutcome,
    FeedbackRecord,
    ModelInfo,
    PolicyDecision,
    PolicyEvaluateRequest,
)
from forecheck.integrations.sdk import (
    POLICY_BUNDLE_HEADER,
    REQUEST_ID_HEADER,
    AsyncForecheckClient,
    ForecheckClient,
    ForecheckClientError,
)

from .conftest import make_context


def _model_info() -> ModelInfo:
    return ModelInfo(
        backend="test",
        model_id="test-model",
        prompt_contract_hash="0" * 16,
        label_schema_version="1.0",
    )


def _classify_response_json(request_id: str | None = None) -> dict[str, Any]:
    response = ClassifyResponse(
        request_id=request_id,
        scores=[],
        model=_model_info(),
        calibration=CalibrationInfo(),
        latency_ms=1.0,
    )
    return response.model_dump(mode="json")


def _error_response_json(
    code: ErrorCode,
    message: str = "boom",
    *,
    retryable: bool = False,
    request_id: str | None = None,
) -> dict[str, Any]:
    envelope = ErrorResponse(
        request_id=request_id, error=ErrorBody(code=code, message=message, retryable=retryable)
    )
    return envelope.model_dump(mode="json")


def _policy_decision_json(decision: str = "allow") -> dict[str, Any]:
    return PolicyDecision(
        decision=decision,  # type: ignore[arg-type]
        matched_rules=[],
        policy_bundle_id="conservative",
        policy_bundle_hash="deadbeef",
    ).model_dump(mode="json")


def test_classify_happy_path() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json=_classify_response_json())

    client = ForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    response = client.classify(ClassifyRequest(context=make_context()))

    assert response.model.model_id == "test-model"
    assert len(seen_requests) == 1
    assert seen_requests[0].url.path == "/v1/classify"
    assert seen_requests[0].method == "POST"


def test_retries_on_retryable_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                503, json=_error_response_json(ErrorCode.MODEL_NOT_READY, retryable=True)
            )
        return httpx.Response(200, json=_classify_response_json())

    client = ForecheckClient(
        "https://forecheck.test", transport=httpx.MockTransport(handler), retries=2
    )
    response = client.classify(ClassifyRequest(context=make_context()))

    assert calls["n"] == 2
    assert response.model.model_id == "test-model"


def test_does_not_retry_on_422() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            422, json=_error_response_json(ErrorCode.VALIDATION_FAILED, retryable=False)
        )

    client = ForecheckClient(
        "https://forecheck.test", transport=httpx.MockTransport(handler), retries=2
    )
    with pytest.raises(ForecheckClientError) as exc_info:
        client.classify(ClassifyRequest(context=make_context()))

    assert calls["n"] == 1
    assert exc_info.value.code is ErrorCode.VALIDATION_FAILED
    assert exc_info.value.status == 422


def test_does_not_retry_a_retryable_flag_on_a_4xx_status() -> None:
    """The task's explicit rule: never retry a 4xx, even if the body claims retryable."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            429, json=_error_response_json(ErrorCode.RATE_LIMITED, retryable=True)
        )

    client = ForecheckClient(
        "https://forecheck.test", transport=httpx.MockTransport(handler), retries=2
    )
    with pytest.raises(ForecheckClientError) as exc_info:
        client.classify(ClassifyRequest(context=make_context()))

    assert calls["n"] == 1
    assert exc_info.value.code is ErrorCode.RATE_LIMITED


def test_error_envelope_maps_to_client_error_with_request_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json=_error_response_json(
                ErrorCode.INTERNAL_ERROR, "server exploded", request_id="rid-1"
            ),
            headers={REQUEST_ID_HEADER: "rid-1"},
        )

    client = ForecheckClient(
        "https://forecheck.test", transport=httpx.MockTransport(handler), retries=0
    )
    with pytest.raises(ForecheckClientError) as exc_info:
        client.classify(ClassifyRequest(context=make_context()))

    assert exc_info.value.code is ErrorCode.INTERNAL_ERROR
    assert exc_info.value.message == "server exploded"
    assert exc_info.value.request_id == "rid-1"


def test_request_id_and_token_and_bundle_headers_are_sent() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request_id"] = request.headers.get(REQUEST_ID_HEADER)
        captured["auth"] = request.headers.get("Authorization")
        captured["bundle"] = request.headers.get(POLICY_BUNDLE_HEADER)
        return httpx.Response(200, json=_policy_decision_json())

    client = ForecheckClient(
        "https://forecheck.test",
        token="secret-token",
        transport=httpx.MockTransport(handler),
    )
    request = PolicyEvaluateRequest(request_id="req-42", context=make_context())
    client.evaluate(request, bundle="balanced")

    assert captured["request_id"] == "req-42"
    assert captured["auth"] == "Bearer secret-token"
    assert captured["bundle"] == "balanced"


def test_classify_and_evaluate_posts_context_only() -> None:
    seen_bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_policy_decision_json())

    client = ForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    decision = client.classify_and_evaluate(make_context())

    assert decision.decision.value == "allow"
    assert seen_bodies[0]["classification"] is None
    assert seen_bodies[0]["context"] is not None


def test_ready_returns_false_on_non_2xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = ForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    assert client.ready() is False


def test_feedback_happy_path() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200, json={"schema_version": "1.0", "feedback_id": "fb-1", "stored": True}
        )

    client = ForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    record = FeedbackRecord(
        request_id="req-1",
        decision=Decision.REVIEW,
        outcome=FeedbackOutcome.APPROVED,
        reviewer_role="support_lead",
    )
    ack = client.feedback(record)

    assert ack.feedback_id == "fb-1"
    assert ack.stored is True
    assert seen_requests[0].url.path == "/v1/feedback"
    assert seen_requests[0].headers.get(REQUEST_ID_HEADER) == "req-1"


async def test_async_feedback_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"schema_version": "1.0", "feedback_id": "fb-2", "stored": True}
        )

    client = AsyncForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    record = FeedbackRecord(
        request_id="req-2",
        decision=Decision.DENY,
        outcome=FeedbackOutcome.ESCALATED,
        reviewer_role="security_oncall",
    )
    ack = await client.feedback(record)
    await client.aclose()

    assert ack.feedback_id == "fb-2"


async def test_async_classify_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_classify_response_json())

    client = AsyncForecheckClient("https://forecheck.test", transport=httpx.MockTransport(handler))
    response = await client.classify(ClassifyRequest(context=make_context()))
    await client.aclose()

    assert response.model.model_id == "test-model"


async def test_async_retries_on_retryable_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                503, json=_error_response_json(ErrorCode.BACKEND_TIMEOUT, retryable=True)
            )
        return httpx.Response(200, json=_classify_response_json())

    async with AsyncForecheckClient(
        "https://forecheck.test", transport=httpx.MockTransport(handler), retries=2
    ) as client:
        response = await client.classify(ClassifyRequest(context=make_context()))

    assert calls["n"] == 2
    assert response.model.model_id == "test-model"
