"""``forecheck evaluate --run <dir> --split <name> --class <evaluation_class> ...``."""

from __future__ import annotations

import random
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
from forecheck.evaluation.score_cache import load_raw_scores, save_raw_scores, score_cache_path
from forecheck.policies.dsl import PolicyBundle

__all__ = ["evaluate_command"]

_SUBSAMPLE_SEED = 20260921


def evaluate_command(
    run: Annotated[Path, typer.Option(file_okay=False)],
    split: Annotated[str, typer.Option()],
    evaluation_class: Annotated[EvaluationClass, typer.Option("--class")],
    backend: Annotated[
        str, typer.Option(help="mock | hf | rule_baseline | encoder | guardian | agent_self")
    ] = "hf",
    backend_config: Annotated[
        Path | None,
        typer.Option(
            "--backend-config", help="YAML config for --backend guardian or --backend agent_self."
        ),
    ] = None,
    strip_identity: Annotated[
        bool,
        typer.Option(
            "--strip-identity",
            help="Omit principal entitlements, agent delegated scopes, delegation chain "
            "and policy text from the rendered context (identity ablation).",
        ),
    ] = False,
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
    max_examples: Annotated[
        int | None,
        typer.Option(
            "--max-examples",
            help="Evaluate a fixed-seed random subsample of this many rows (slow backends).",
        ),
    ] = None,
    stacking_bundles: Annotated[
        str | None,
        typer.Option(
            "--stacking-bundles",
            help="Comma-separated policy bundle names or paths to stack, k=1..K.",
        ),
    ] = None,
    stacking_synthetic: Annotated[
        bool,
        typer.Option(
            "--stacking-synthetic",
            help="Append 11 synthetic single-dimension policies to the stacking bundles.",
        ),
    ] = False,
    compare_report: Annotated[
        Path | None,
        typer.Option(
            "--compare-report",
            help="forecheck report.json for the same split, added as a side-by-side "
            "delta to the --backend agent_self self-judgment section.",
        ),
    ] = None,
    dump_n: Annotated[
        int | None,
        typer.Option(
            "--dump-n",
            help="Greedily generate verdict+reason for this many examples and dump "
            "to a jsonl (--backend agent_self only).",
        ),
    ] = None,
) -> None:
    """Score ``split`` with ``backend``, apply any fitted calibration, and write reports."""
    if backend in ("guardian", "agent_self"):
        run.mkdir(parents=True, exist_ok=True)
    elif not run.exists():
        raise typer.BadParameter(f"--run {run} does not exist")
    data_dir = resolve_data_dir(data, run)
    split_path = data_dir / f"{split}.jsonl"
    examples = read_jsonl(split_path)
    if not examples:
        raise typer.BadParameter(f"no examples found at {split_path}")
    if max_examples is not None and max_examples < len(examples):
        examples = random.Random(_SUBSAMPLE_SEED).sample(examples, max_examples)  # noqa: S311
        typer.echo(f"evaluating a seeded subsample of {max_examples} rows from {split}")
    selection_examples = None
    if threshold_split != "none":
        if threshold_split == split:
            raise typer.BadParameter("--threshold-split must differ from --split")
        selection_path = data_dir / f"{threshold_split}.jsonl"
        if not selection_path.exists():
            raise typer.BadParameter(f"threshold split not found at {selection_path}")
        selection_examples = read_jsonl(selection_path)

    backend_instance = resolve_backend(
        backend, run, config=backend_config, strip_identity=strip_identity
    )
    calibrator_bundle = None
    calibrators = None
    bundle_path = run / "calibration" / "bundle.json"
    if strip_identity:
        typer.echo(
            "skipping calibration bundle: --strip-identity was set; "
            "calibration was fitted on full context"
        )
    elif bundle_path.exists():
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

    stack_bundles: list[PolicyBundle] = []
    if stacking_bundles:
        names = [name.strip() for name in stacking_bundles.split(",") if name.strip()]
        stack_bundles = [load_policy_engine_by_name_or_path(name).bundle for name in names]

    selection_scores = None
    on_selection_scored = None
    if selection_examples is not None and threshold_split != "none":
        info = backend_instance.model_info
        cache_path = score_cache_path(
            run,
            split=threshold_split,
            dataset_sha256=sha256_file(data_dir / f"{threshold_split}.jsonl"),
            model_id=info.model_id,
            prompt_contract_hash=info.prompt_contract_hash,
            strip_identity=strip_identity,
        )
        selection_scores = load_raw_scores(cache_path, len(selection_examples))
        if selection_scores is not None:
            typer.echo(f"reusing cached {threshold_split} scores from {cache_path}")
        else:
            on_selection_scored = lambda raw: save_raw_scores(cache_path, raw)  # noqa: E731

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
            identity_stripped=strip_identity,
            threshold_selection_scores=selection_scores,
            on_threshold_selection_scored=on_selection_scored,
            stacking_bundles=stack_bundles,
            stacking_synthetic=stacking_synthetic,
        )
        if backend == "agent_self" and dump_n:
            from forecheck.inference.agent_self import AgentSelfBackend

            if isinstance(backend_instance, AgentSelfBackend):
                dump_path = (out or (run / "reports" / split)) / "agent_self_dump.jsonl"
                backend_instance.dump_verdicts(examples[:dump_n], dump_path)
    finally:
        backend_instance.close()

    out_dir = out or (run / "reports" / split)
    out_dir.mkdir(parents=True, exist_ok=True)
    report.to_json(out_dir / "report.json")
    report.to_markdown(out_dir / "report.md")
    if backend == "agent_self":
        from forecheck.evaluation.report import EvaluationReport
        from forecheck.inference.agent_self import render_self_judgment_section

        compare = (
            EvaluationReport.model_validate_json(compare_report.read_text(encoding="utf-8"))
            if compare_report is not None
            else None
        )
        section = render_self_judgment_section(report, compare)
        with (out_dir / "report.md").open("a", encoding="utf-8") as f:
            f.write("\n" + section)
    typer.echo(f"macro auprc={report.macro.get('auprc')}, macro ece={report.macro.get('ece')}")
    typer.echo(f"wrote {out_dir / 'report.json'} and {out_dir / 'report.md'}")
