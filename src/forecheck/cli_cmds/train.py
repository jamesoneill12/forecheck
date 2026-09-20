"""``forecheck train --config <yaml> [key=value ...]``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.training.config import load_config

__all__ = ["train_command"]


def train_command(
    config: Annotated[Path, typer.Option(exists=True, help="TrainConfig YAML.")],
    overrides: Annotated[
        list[str] | None, typer.Argument(help="Dotted key.sub=value overrides.")
    ] = None,
) -> None:
    """Load a config, apply dotted overrides, and run LoRA training."""
    train_config = load_config(config, overrides or [])
    from forecheck.training.loop import run_training

    try:
        result = run_training(train_config)
    except ImportError as exc:
        typer.echo(f"forecheck train requires the 'train' extra: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"training complete: {result.steps_completed} steps, "
        f"best_step={result.best_step}, run_dir={result.run_dir}"
    )
