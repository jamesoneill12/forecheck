from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from forecheck.api.feedback import JsonlFeedbackSink

if TYPE_CHECKING:
    from pathlib import Path


def _feedback_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "request_id": "req-1",
        "decision": "review",
        "outcome": "approved",
        "reviewer_role": "support_lead",
    }
    body.update(overrides)
    return body


async def test_submit_feedback_returns_ack(client_factory: Any, tmp_path: Path) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    response = await client.post("/v1/feedback", json=_feedback_body())
    assert response.status_code == 200
    body = response.json()
    assert body["stored"] is True
    assert body["feedback_id"]


async def test_submit_feedback_assigns_id_when_missing(client_factory: Any, tmp_path: Path) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    response = await client.post("/v1/feedback", json=_feedback_body())
    feedback_id = response.json()["feedback_id"]

    sink = JsonlFeedbackSink(tmp_path)
    stored = sink.read_since()
    assert len(stored) == 1
    assert stored[0].feedback_id == feedback_id
    assert stored[0].request_id == "req-1"
    assert stored[0].outcome.value == "approved"


async def test_submit_feedback_persists_optional_fields(
    client_factory: Any, tmp_path: Path
) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    body = _feedback_body(
        corrected_labels={"prompt_injection_influence": "yes"},
        reason="reviewer disagreed with the score",
        policy_bundle_id="balanced",
        policy_bundle_version=1,
        calibration_version="cal-v3",
        model_id="mock-heuristic-v1",
    )
    response = await client.post("/v1/feedback", json=body)
    assert response.status_code == 200

    stored = JsonlFeedbackSink(tmp_path).read_since()
    assert stored[0].corrected_labels == {"prompt_injection_influence": "yes"}
    assert stored[0].reason == "reviewer disagreed with the score"
    assert stored[0].policy_bundle_id == "balanced"
    assert stored[0].policy_bundle_version == 1


async def test_submit_feedback_reason_over_limit_is_422(
    client_factory: Any, tmp_path: Path
) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    body = _feedback_body(reason="x" * 1025)
    response = await client.post("/v1/feedback", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


async def test_submit_feedback_unknown_outcome_is_422(client_factory: Any, tmp_path: Path) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    body = _feedback_body(outcome="withdrawn")
    response = await client.post("/v1/feedback", json=body)
    assert response.status_code == 422


async def test_feedback_audit_event_omits_reason_text(
    client_factory: Any, tmp_path: Path, capsys: Any
) -> None:
    client = await client_factory(feedback_sink_path=tmp_path)
    body = _feedback_body(reason="contains a secret token abc123")
    response = await client.post("/v1/feedback", json=body)
    assert response.status_code == 200

    captured = capsys.readouterr().out
    assert "contains a secret token abc123" not in captured
    assert "forecheck_audit" in captured


def test_jsonl_feedback_sink_round_trips(tmp_path: Path) -> None:
    from forecheck.contracts import Decision, FeedbackOutcome, FeedbackRecord

    sink = JsonlFeedbackSink(tmp_path)
    record = FeedbackRecord(
        request_id="r1",
        decision=Decision.ALLOW,
        outcome=FeedbackOutcome.EXPIRED,
        reviewer_role="lead",
    )
    sink.append(record)
    sink.append(record.model_copy(update={"request_id": "r2"}))

    stored = sink.read_since()
    assert [r.request_id for r in stored] == ["r1", "r2"]

    stored_json = json.loads(sink.path.read_text(encoding="utf-8").splitlines()[0])
    assert stored_json["request_id"] == "r1"
