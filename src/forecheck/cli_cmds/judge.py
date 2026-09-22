"""``forecheck judge sample|label|agreement``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from forecheck.data.io import read_jsonl
from forecheck.judge.agreement import compute_agreement, find_disagreements, write_agreement_report
from forecheck.judge.labeling import label_examples, load_label_cache, write_label_rows
from forecheck.judge.sampling import render_coverage_table, stratified_sample
from forecheck.judge.schema import read_sample_rows, write_sample_rows

__all__ = ["judge_app"]

judge_app = typer.Typer(
    no_args_is_help=True,
    help="Independent LLM-judge labelling of a stratified eval sample.",
)


@judge_app.command("sample")
def sample_command(
    data: Annotated[Path, typer.Option(exists=True, file_okay=False, help="Dataset directory.")],
    splits: Annotated[str, typer.Option(help="Comma-separated split names to sample from.")],
    n: Annotated[int, typer.Option(help="Target number of examples to sample.")] = 600,
    seed: Annotated[int, typer.Option(help="Sampler seed.")] = 20260922,
    out: Annotated[Path, typer.Option(help="Output sample jsonl path.")] = Path(
        "judge_sample.jsonl"
    ),
    cell_target: Annotated[
        int,
        typer.Option(
            "--cell-target",
            help="Minimum rows per (dimension, label) cell where that many are available.",
        ),
    ] = 20,
) -> None:
    """Draw a stratified, coverage-maximising sample for independent LLM-judge labelling."""
    split_names = [s.strip() for s in splits.split(",") if s.strip()]
    if not split_names:
        raise typer.BadParameter("--splits must name at least one split")

    examples = []
    for split_name in split_names:
        path = data / f"{split_name}.jsonl"
        if not path.exists():
            raise typer.BadParameter(f"split file not found: {path}")
        examples.extend(read_jsonl(path))
    if not examples:
        raise typer.BadParameter(f"no examples found under {data} for splits {split_names}")

    result = stratified_sample(examples, n=n, seed=seed, cell_target=cell_target)
    write_sample_rows(out, result.rows)
    coverage_path = out.parent / "coverage.json"
    coverage_path.write_text(json.dumps(result.coverage, indent=2), encoding="utf-8")

    typer.echo(render_coverage_table(result.coverage))
    typer.echo(f"wrote {len(result.rows)} rows -> {out}")


@judge_app.command("label")
def label_command(
    sample: Annotated[Path, typer.Option(exists=True, help="Sample jsonl from 'judge sample'.")],
    model: Annotated[str, typer.Option(help="Judge model id.")],
    out: Annotated[
        Path, typer.Option(help="Output labels jsonl; also read back in as the idempotency cache.")
    ],
    provider: Annotated[str, typer.Option(help="openai_compat | anthropic")] = "openai_compat",
    strip_identity: Annotated[
        bool, typer.Option("--strip-identity", help="Judge the identity-stripped rendering.")
    ] = False,
    concurrency: Annotated[int, typer.Option(help="Concurrent judge calls.")] = 8,
    max_examples: Annotated[
        int | None, typer.Option("--max-examples", help="Label only the first N sample rows.")
    ] = None,
) -> None:
    """Label a sample with a frontier LLM judge, caching by (model, example_id, strip_identity)."""
    if provider not in ("openai_compat", "anthropic"):
        raise typer.BadParameter("--provider must be one of: openai_compat, anthropic")

    rows = read_sample_rows(sample)
    if not rows:
        raise typer.BadParameter(f"no rows found at {sample}")
    if max_examples is not None:
        rows = rows[:max_examples]

    cache = load_label_cache(out)
    result = label_examples(
        rows,
        provider_name=provider,
        model=model,
        strip_identity=strip_identity,
        concurrency=concurrency,
        cache=cache,
    )
    write_label_rows(out, result.rows)

    n_new = len(result.new_rows)
    n_cached = len(result.rows) - n_new
    input_tokens = sum(r.input_tokens for r in result.new_rows)
    output_tokens = sum(r.output_tokens for r in result.new_rows)
    known_costs = [r.cost_usd for r in result.new_rows if r.cost_usd is not None]

    typer.echo(f"labelled {len(result.rows)} examples ({n_new} new, {n_cached} cached)")
    typer.echo(f"this run: input_tokens={input_tokens} output_tokens={output_tokens}")
    if n_new and len(known_costs) == n_new:
        typer.echo(f"estimated cost: ${sum(known_costs):.4f}")
    elif n_new:
        typer.echo(f"estimated cost: unknown for model {model!r}; token totals above are exact")

    n_unparseable = sum(1 for r in result.rows if not r.parse_ok)
    if n_unparseable:
        typer.echo(f"warning: {n_unparseable} example(s) never parsed into valid JSON after retry")
    typer.echo(f"wrote {out}")


@judge_app.command("agreement")
def agreement_command(
    sample: Annotated[Path, typer.Option(exists=True, help="Sample jsonl from 'judge sample'.")],
    labels: Annotated[
        Path, typer.Option(exists=True, help="Judge labels jsonl from 'judge label'.")
    ],
    out: Annotated[Path, typer.Option(file_okay=False, help="Output directory for the report.")],
) -> None:
    """Compare judge labels against generator labels: kappa, agreement %, confusion,
    disagreements."""
    sample_rows = read_sample_rows(sample)
    label_rows = list(load_label_cache(labels).values())
    if not sample_rows:
        raise typer.BadParameter(f"no rows found at {sample}")
    if not label_rows:
        raise typer.BadParameter(f"no rows found at {labels}")

    report = compute_agreement(sample_rows, label_rows)
    disagreements = find_disagreements(sample_rows, label_rows)
    write_agreement_report(out, report, disagreements)

    for dimension, dm in report.dimensions.items():
        typer.echo(
            f"{dimension.value}: kappa={dm.cohen_kappa} agreement={dm.agreement_rate} "
            f"n={dm.n_compared} unparseable={dm.n_unparseable}"
        )
    typer.echo(f"{len(disagreements)} disagreement(s) written to {out / 'disagreements.jsonl'}")
    typer.echo(f"wrote {out / 'agreement.md'} and {out / 'agreement.json'}")
