"""``forecheck feedback export`` — read back the feedback sink for offline analysis."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from forecheck.api.feedback import DEFAULT_FEEDBACK_FILENAME, JsonlFeedbackSink

__all__ = ["feedback_app"]

feedback_app = typer.Typer(no_args_is_help=True, help="Feedback sink utilities.")


@feedback_app.command("export")
def export(
    directory: Annotated[
        Path,
        typer.Option("--sink-dir", exists=True, file_okay=False, help="Feedback sink directory."),
    ],
    since: Annotated[
        datetime | None,
        typer.Option("--since", help="Only records at/after this ISO 8601 timestamp."),
    ] = None,
    output_format: Annotated[
        str, typer.Option("--format", help="Only 'jsonl' is supported.")
    ] = "jsonl",
    filename: Annotated[str, typer.Option("--filename")] = DEFAULT_FEEDBACK_FILENAME,
) -> None:
    """Print every feedback record at/after ``--since`` as JSON lines to stdout."""
    if output_format != "jsonl":
        raise typer.BadParameter("only --format jsonl is supported")
    sink = JsonlFeedbackSink(directory, filename)
    for record in sink.read_since(since):
        typer.echo(json.dumps(record.model_dump(mode="json"), sort_keys=True))
