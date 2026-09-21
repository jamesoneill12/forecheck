"""forecheck CLI entry point.

``app`` is the registration point for every subcommand group.
"""

from __future__ import annotations

import os
from typing import Annotated

import typer
import uvicorn

from forecheck.cli_cmds.calibrate import calibrate_command
from forecheck.cli_cmds.data import data_app
from forecheck.cli_cmds.evaluate import evaluate_command
from forecheck.cli_cmds.model_card import model_card_command
from forecheck.cli_cmds.policy import policy_app
from forecheck.cli_cmds.train import train_command
from forecheck.cli_cmds.train_encoder import train_encoder_command
from forecheck.contracts import LABEL_SCHEMA_VERSION, SCHEMA_VERSION
from forecheck.version import PROMPT_CONTRACT_VERSION, __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="forecheck: a calibrated pre-execution risk model for AI-agent actions.",
)

app.add_typer(data_app, name="data")
app.add_typer(policy_app, name="policy")
app.command("train")(train_command)
app.command("train-encoder")(train_encoder_command)
app.command("calibrate")(calibrate_command)
app.command("evaluate")(evaluate_command)
app.command("model-card")(model_card_command)


@app.command()
def serve(
    backend: Annotated[str, typer.Option(help="mock | hf | rule_baseline")] = "mock",
    host: Annotated[str, typer.Option()] = "0.0.0.0",  # noqa: S104
    port: Annotated[int, typer.Option()] = 8000,
    policy_bundle: Annotated[str, typer.Option("--policy-bundle")] = "conservative",
    calibration: Annotated[str | None, typer.Option("--calibration")] = None,
    model_id: Annotated[str | None, typer.Option("--model-id")] = None,
    adapter_id: Annotated[str | None, typer.Option("--adapter-id")] = None,
    device: Annotated[str, typer.Option()] = "auto",
    workers: Annotated[int, typer.Option()] = 1,
) -> None:
    """Start the forecheck FastAPI service with uvicorn."""
    env: dict[str, str] = {
        "FORECHECK_BACKEND": backend,
        "FORECHECK_HOST": host,
        "FORECHECK_PORT": str(port),
        "FORECHECK_POLICY_BUNDLE": policy_bundle,
        "FORECHECK_DEVICE": device,
    }
    if calibration is not None:
        env["FORECHECK_CALIBRATION_PATH"] = calibration
    if model_id is not None:
        env["FORECHECK_MODEL_ID"] = model_id
    if adapter_id is not None:
        env["FORECHECK_ADAPTER_ID"] = adapter_id
    os.environ.update(env)

    uvicorn.run(
        "forecheck.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        workers=workers,
    )


@app.command()
def version() -> None:
    """Print forecheck's version, schema version, label schema version and prompt
    contract version."""
    typer.echo(f"forecheck {__version__}")
    typer.echo(f"schema_version={SCHEMA_VERSION}")
    typer.echo(f"label_schema_version={LABEL_SCHEMA_VERSION}")
    typer.echo(f"prompt_contract_version={PROMPT_CONTRACT_VERSION}")


if __name__ == "__main__":
    app()
