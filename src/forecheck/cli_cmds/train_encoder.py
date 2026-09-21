"""``forecheck train-encoder --config <yaml> [key=value ...]``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.training.config import load_encoder_config

__all__ = ["train_encoder_command"]


def train_encoder_command(
    config: Annotated[Path, typer.Option(exists=True, help="EncoderTrainConfig YAML.")],
    overrides: Annotated[
        list[str] | None, typer.Argument(help="Dotted key.sub=value overrides.")
    ] = None,
) -> None:
    """Load a config, apply dotted overrides, and train the encoder classifier arm."""
    train_config = load_encoder_config(config, overrides or [])
    from forecheck.training.encoder_loop import run_encoder_training

    try:
        result = run_encoder_training(train_config)
    except ImportError as exc:
        typer.echo(f"forecheck train-encoder requires the 'train' extra: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"encoder training complete: {result.steps_completed} steps, "
        f"best_step={result.best_step}, run_dir={result.run_dir}"
    )
