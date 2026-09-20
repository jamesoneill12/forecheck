"""``forecheck data generate|split|verify``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.contracts import DatasetManifest, Example, Split, UsageRestriction
from forecheck.data.io import (
    build_manifest,
    read_jsonl,
    verify_manifest,
    write_jsonl,
    write_manifests,
)
from forecheck.data.splitting import LeakageError, assert_no_leakage, split_examples
from forecheck.generation.config import build_jobs, load_generation_config
from forecheck.generation.pipeline import GenerationPipeline, PipelineConfig
from forecheck.generation.renderers import OfflineTemplateRenderer

__all__ = ["data_app"]

data_app = typer.Typer(no_args_is_help=True, help="Generate, split and verify synthetic datasets.")

_RAW_FILENAME = "raw.jsonl"


@data_app.command("generate")
def generate(
    config: Annotated[Path, typer.Option(exists=True, help="GenerationConfig YAML.")],
    out: Annotated[Path, typer.Option(help="Output directory; writes raw.jsonl.")],
    offline: Annotated[bool, typer.Option(help="Use the offline template renderer.")] = True,
    seed: Annotated[int | None, typer.Option(help="Override the config file's seed.")] = None,
) -> None:
    """Generate a raw (unsplit) dataset from a :class:`GenerationConfig` YAML file."""
    if not offline:
        raise typer.BadParameter("only --offline generation is implemented; omit --online")
    gen_config = load_generation_config(config, seed_override=seed)
    jobs = build_jobs(gen_config)
    raw_path = out / _RAW_FILENAME
    raw_path.unlink(missing_ok=True)
    pipeline_config = PipelineConfig(
        master_seed=gen_config.seed, output_path=raw_path, cache_dir=out / ".cache"
    )
    pipeline = GenerationPipeline(pipeline_config)
    examples = pipeline.run(jobs, OfflineTemplateRenderer())
    typer.echo(f"generated {len(examples)} examples -> {raw_path}")


@data_app.command("split")
def split(directory: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Split a raw dataset produced by ``generate`` into leakage-safe splits + manifests."""
    raw_path = directory / _RAW_FILENAME
    if not raw_path.exists():
        raise typer.BadParameter(f"{raw_path} not found; run 'forecheck data generate' first")
    examples = read_jsonl(raw_path)
    splits = split_examples(examples)
    assert_no_leakage(splits)
    manifests: list[DatasetManifest] = []
    for split_value, rows in splits.items():
        if not rows:
            continue
        path = directory / f"{split_value.value}.jsonl"
        write_jsonl(path, rows)
        manifests.append(build_manifest(split_value, path, rows))
        typer.echo(f"{split_value.value}: {len(rows)} rows -> {path}")
    write_manifests(directory, manifests)
    raw_path.unlink()


def _load_manifests(directory: Path) -> list[DatasetManifest]:
    return [
        DatasetManifest.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.manifest.json"))
    ]


def _usage_violations(splits: dict[Split, list[Example]]) -> list[str]:
    violations: list[str] = []
    for split_value in (Split.TRAIN, Split.CALIBRATION):
        for example in splits.get(split_value, []):
            if example.license.usage is UsageRestriction.EVAL_ONLY:
                violations.append(
                    f"{example.example_id} is eval_only but present in {split_value.value}"
                )
            if example.license.canary_present:
                violations.append(
                    f"{example.example_id} carries a canary but present in {split_value.value}"
                )
    return violations


@data_app.command("verify")
def verify(directory: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Verify manifests, leakage-freedom, and that no eval_only/canary row leaked into
    train/calibration."""
    manifests = _load_manifests(directory)
    if not manifests:
        raise typer.BadParameter(f"no *.manifest.json files found in {directory}")
    splits: dict[Split, list[Example]] = {}
    for manifest in manifests:
        path = directory / f"{manifest.split.value}.jsonl"
        if not verify_manifest(manifest, path):
            typer.echo(f"FAIL: {path} does not match its manifest sha256", err=True)
            raise typer.Exit(code=1)
        splits[manifest.split] = read_jsonl(path)
    try:
        assert_no_leakage(splits)
    except LeakageError as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    violations = _usage_violations(splits)
    if violations:
        for violation in violations:
            typer.echo(f"FAIL: {violation}", err=True)
        raise typer.Exit(code=1)
    n_total = sum(len(rows) for rows in splits.values())
    typer.echo(
        f"OK: {len(manifests)} splits ({n_total} examples) verified; "
        "no leakage; no eval_only/canary rows in train/calibration"
    )
