"""``forecheck calibrate --run <dir> --split calibration [--backend mock|hf] [--data <dir>]``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.calibration.fit import fit_bundle
from forecheck.calibration.store import save_bundle
from forecheck.cli_cmds._common import resolve_backend, resolve_data_dir
from forecheck.contracts import CalibrationMethod, LabelValue, RiskDimension
from forecheck.data.io import read_jsonl, sha256_file

__all__ = ["calibrate_command"]


def calibrate_command(
    run: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    split: Annotated[str, typer.Option()] = "calibration",
    backend: Annotated[str, typer.Option(help="mock | hf | rule_baseline | encoder")] = "hf",
    data: Annotated[Path | None, typer.Option(help="Dataset directory.")] = None,
    method: Annotated[CalibrationMethod, typer.Option()] = CalibrationMethod.TEMPERATURE,
) -> None:
    """Score ``split`` with ``backend`` and fit a calibration bundle onto ``<run>/calibration``."""
    data_dir = resolve_data_dir(data, run)
    split_path = data_dir / f"{split}.jsonl"
    examples = read_jsonl(split_path)
    if not examples:
        raise typer.BadParameter(f"no examples found at {split_path}")

    backend_instance = resolve_backend(backend, run)
    try:
        raw_scores = backend_instance.score_batch([e.context for e in examples])
        scores: dict[RiskDimension, list[float]] = {d: [] for d in RiskDimension}
        labels: dict[RiskDimension, list[LabelValue]] = {d: [] for d in RiskDimension}
        for example, raw in zip(examples, raw_scores, strict=True):
            for dimension in RiskDimension:
                value = raw.scores.get(dimension)
                if value is None:
                    continue
                scores[dimension].append(value)
                labels[dimension].append(example.labels.values[dimension])
        report = fit_bundle(
            scores,
            labels,
            method,
            backend_model_id=backend_instance.model_info.model_id,
            prompt_contract_hash=backend_instance.model_info.prompt_contract_hash,
            dataset_sha256=sha256_file(split_path),
            split_name=split,
        )
    finally:
        backend_instance.close()

    out_dir = run / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_bundle(report.bundle, out_dir / "bundle.json")
    typer.echo(f"fitted calibration on {len(examples)} examples from split {split!r}")
    typer.echo(f"macro ECE {report.macro_ece_before:.4f} -> {report.macro_ece_after:.4f}")
    for warning in report.warnings:
        typer.echo(f"warning: {warning}")
    typer.echo(f"wrote {out_dir / 'bundle.json'}")
