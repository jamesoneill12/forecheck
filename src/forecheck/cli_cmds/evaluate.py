"""``forecheck evaluate --run <dir> --split <name> --class <evaluation_class> ...``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.calibration.store import load_bundle
from forecheck.cli_cmds._common import (
    calibrators_from_bundle,
    load_policy_engine_by_name_or_path,
    resolve_backend,
    resolve_data_dir,
)
from forecheck.data.io import read_jsonl, sha256_file
from forecheck.evaluation.report import EvaluationClass
from forecheck.evaluation.runner import evaluate

__all__ = ["evaluate_command"]


def evaluate_command(
    run: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    split: Annotated[str, typer.Option()],
    evaluation_class: Annotated[EvaluationClass, typer.Option("--class")],
    backend: Annotated[str, typer.Option(help="mock | hf | rule_baseline")] = "hf",
    bundle: Annotated[str | None, typer.Option(help="Policy bundle name or path.")] = None,
    data: Annotated[Path | None, typer.Option(help="Dataset directory.")] = None,
    out: Annotated[Path | None, typer.Option(help="Report output directory.")] = None,
    threshold_split: Annotated[
        str,
        typer.Option(
            help="Split used to select per-dimension decision thresholds; 'none' disables. "
            "Must differ from --split."
        ),
    ] = "dev",
) -> None:
    """Score ``split`` with ``backend``, apply any fitted calibration, and write reports."""
    data_dir = resolve_data_dir(data, run)
    split_path = data_dir / f"{split}.jsonl"
    examples = read_jsonl(split_path)
    if not examples:
        raise typer.BadParameter(f"no examples found at {split_path}")
    selection_examples = None
    if threshold_split != "none":
        if threshold_split == split:
            raise typer.BadParameter("--threshold-split must differ from --split")
        selection_path = data_dir / f"{threshold_split}.jsonl"
        if not selection_path.exists():
            raise typer.BadParameter(f"threshold split not found at {selection_path}")
        selection_examples = read_jsonl(selection_path)

    backend_instance = resolve_backend(backend, run)
    calibrator_bundle = None
    calibrators = None
    bundle_path = run / "calibration" / "bundle.json"
    if bundle_path.exists():
        loaded = load_bundle(bundle_path)
        if loaded.backend_model_id == backend_instance.model_info.model_id:
            calibrator_bundle = loaded
            calibrators = calibrators_from_bundle(loaded)
        else:
            typer.echo(
                f"skipping calibration bundle fitted for {loaded.backend_model_id!r}; "
                f"backend is {backend_instance.model_info.model_id!r}"
            )
    engine = load_policy_engine_by_name_or_path(bundle) if bundle is not None else None

    try:
        report = evaluate(
            backend_instance,
            examples,
            evaluation_class=evaluation_class,
            calibrators=calibrators,
            calibrator_bundle=calibrator_bundle,
            engine=engine,
            dataset_sha256=sha256_file(split_path),
            threshold_selection_examples=selection_examples,
        )
    finally:
        backend_instance.close()

    out_dir = out or (run / "reports" / split)
    out_dir.mkdir(parents=True, exist_ok=True)
    report.to_json(out_dir / "report.json")
    report.to_markdown(out_dir / "report.md")
    typer.echo(f"macro auprc={report.macro.get('auprc')}, macro ece={report.macro.get('ece')}")
    typer.echo(f"wrote {out_dir / 'report.json'} and {out_dir / 'report.md'}")
