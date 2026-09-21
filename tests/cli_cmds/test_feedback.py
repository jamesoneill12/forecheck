from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from forecheck.api.feedback import JsonlFeedbackSink
from forecheck.cli import app
from forecheck.contracts import Decision, FeedbackOutcome, FeedbackRecord

runner = CliRunner()


def _record(request_id: str) -> FeedbackRecord:
    return FeedbackRecord(
        request_id=request_id,
        decision=Decision.REVIEW,
        outcome=FeedbackOutcome.APPROVED,
        reviewer_role="support_lead",
    )


def test_export_prints_every_stored_record(tmp_path: Path) -> None:
    sink = JsonlFeedbackSink(tmp_path)
    sink.append(_record("r1"))
    sink.append(_record("r2"))

    result = runner.invoke(app, ["feedback", "export", "--sink-dir", str(tmp_path)])

    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    assert {json.loads(line)["request_id"] for line in lines} == {"r1", "r2"}


def test_export_since_in_the_future_excludes_everything(tmp_path: Path) -> None:
    sink = JsonlFeedbackSink(tmp_path)
    sink.append(_record("old"))

    result = runner.invoke(
        app,
        ["feedback", "export", "--sink-dir", str(tmp_path), "--since", "2999-01-01T00:00:00"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_export_rejects_non_jsonl_format(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["feedback", "export", "--sink-dir", str(tmp_path), "--format", "csv"]
    )
    assert result.exit_code != 0
