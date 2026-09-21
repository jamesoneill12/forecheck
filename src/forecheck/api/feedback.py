"""Pluggable sink for human feedback on forecheck decisions (the label flywheel).

The default sink appends one JSON line per :class:`FeedbackRecord` to a file under a
configured directory. No credentials, no network: a deployment points
``FORECHECK_FEEDBACK_SINK_PATH`` at any writable location, including a mounted volume a
separate process ships elsewhere. A custom :class:`FeedbackSink` can replace it wholesale
by constructing :class:`~forecheck.api.deps.AppState` differently.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from forecheck.contracts.io import FeedbackRecord

__all__ = ["FeedbackSink", "JsonlFeedbackSink"]

DEFAULT_FEEDBACK_FILENAME = "feedback.jsonl"


class FeedbackSink(Protocol):
    def append(self, record: FeedbackRecord) -> None: ...

    def read_since(self, since: datetime | None = None) -> list[FeedbackRecord]: ...


class JsonlFeedbackSink:
    """Appends to, and reads back from, a single JSONL file."""

    def __init__(self, directory: Path, filename: str = DEFAULT_FEEDBACK_FILENAME) -> None:
        self._path = directory / filename

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: FeedbackRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")

    def read_since(self, since: datetime | None = None) -> list[FeedbackRecord]:
        if not self._path.exists():
            return []
        if since is not None and since.tzinfo is None:
            since = since.replace(tzinfo=UTC)
        records: list[FeedbackRecord] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = FeedbackRecord.model_validate_json(line)
            if since is None or record.created_at >= since:
                records.append(record)
        return records
