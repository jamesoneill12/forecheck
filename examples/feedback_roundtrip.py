"""REVIEW -> human decision -> feedback round trip.

Demonstrates the label flywheel end to end: forecheck classifies and policy-evaluates a
proposed action, a human reviewer records a real-world outcome on the resulting
``REVIEW``, and that outcome is submitted back via ``POST /v1/feedback`` so it becomes a
label for future recalibration and threshold refitting -- never a change to the
decision that already happened.

Runs entirely offline: an ``httpx.MockTransport`` answers every request using a
``LocalForecheck`` instance (mock backend, uncalibrated) and a real
``JsonlFeedbackSink`` writing to a temp directory. The mock backend is not a trained
model and the resulting scores are not calibrated probabilities, which is exactly why
the ``balanced`` bundle's ``uncalibrated_decision`` (``review``) fires here regardless
of the underlying scores -- see ``docs/product-spec.md`` §7.1.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import httpx

from forecheck.api.feedback import JsonlFeedbackSink
from forecheck.contracts import (
    ClassifyRequest,
    Decision,
    FeedbackOutcome,
    FeedbackRecord,
    PolicyEvaluateRequest,
    PrincipalType,
)
from forecheck.integrations.context_builder import ActionContextBuilder
from forecheck.integrations.local import LocalForecheck
from forecheck.integrations.sdk import ForecheckClient


def build_risky_context() -> Any:
    return (
        ActionContextBuilder()
        .objective("Reply to the vendor thread with the requested invoice copy", explicit=True)
        .principal("user-1", type=PrincipalType.HUMAN, roles=["support_agent"])
        .agent("agent-1", delegated_scopes=["email:send"])
        .propose("send_email", arguments={"to": "vendor@unknown-partner.example"})
        .build()
    )


def make_mock_transport(forecheck: LocalForecheck, sink: JsonlFeedbackSink) -> httpx.MockTransport:
    """A tiny fake server: forwards classify/evaluate to LocalForecheck and feedback to
    a real JsonlFeedbackSink, exactly what the FastAPI route does in the real service."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/classify":
            body = ClassifyRequest.model_validate_json(request.content)
            return httpx.Response(200, json=forecheck.classify(body).model_dump(mode="json"))
        if request.url.path == "/v1/policies/evaluate":
            body = PolicyEvaluateRequest.model_validate_json(request.content)
            return httpx.Response(200, json=forecheck.evaluate(body).model_dump(mode="json"))
        if request.url.path == "/v1/feedback":
            record = FeedbackRecord.model_validate_json(request.content)
            if record.feedback_id is None:
                record = record.model_copy(update={"feedback_id": "fb-demo-1"})
            sink.append(record)
            return httpx.Response(
                200,
                json={
                    "schema_version": "1.0",
                    "feedback_id": record.feedback_id,
                    "stored": True,
                },
            )
        return httpx.Response(
            404,
            json={
                "schema_version": "1.0",
                "error": {"code": "internal_error", "message": "no route", "retryable": False},
            },
        )

    return httpx.MockTransport(handler)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sink = JsonlFeedbackSink(Path(tmp))
        forecheck = LocalForecheck(bundle="balanced")
        transport = make_mock_transport(forecheck, sink)

        with ForecheckClient("https://forecheck.example", transport=transport) as client:
            context = build_risky_context()
            decision = client.classify_and_evaluate(context, request_id="req-1")
            print("decision:", decision.decision.value)
            assert decision.decision is Decision.REVIEW

            record = FeedbackRecord(
                request_id="req-1",
                decision=decision.decision,
                outcome=FeedbackOutcome.APPROVED,
                reviewer_role="support_lead",
                reason="Vendor identity confirmed by phone; destination is a known partner.",
                policy_bundle_id=decision.policy_bundle_id,
            )
            ack = client.feedback(record)
            print("feedback stored:", ack.stored, "feedback_id:", ack.feedback_id)

        stored = sink.read_since()
        print("sink now holds", len(stored), "feedback record(s)")


if __name__ == "__main__":
    main()
