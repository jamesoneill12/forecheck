"""``forecheck external agentdojo`` — port AgentDojo run traces to forecheck Examples."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.data.io import write_jsonl
from forecheck.external.agentdojo import (
    iter_trace_files,
    label_call,
    load_ground_truth,
    overlay_identity,
    parse_trace,
    to_example,
)

__all__ = ["external_app"]

external_app = typer.Typer(no_args_is_help=True, help="Port external agent-safety benchmarks.")


def _render_table(manifest: dict) -> str:
    lines = [f"examples: {manifest['n_examples']}", "", "label counts per dimension:"]
    for dimension, counts in manifest["per_dimension"].items():
        counted = ", ".join(f"{value}={n}" for value, n in counts.items() if n)
        lines.append(f"  {dimension}: {counted}")
    lines.append("")
    lines.append("examples per attack_type:")
    for attack_type, n in sorted(manifest["per_attack_type"].items()):
        lines.append(f"  {attack_type}: {n}")
    lines.append("")
    yes_calls = manifest["prompt_injection_yes_calls"]
    lines.append(f"injection-run calls with prompt_injection_influence=yes: {yes_calls}")
    lines.append(f"injection runs with security=true: {manifest['security_true_runs']}")
    return "\n".join(lines)


@external_app.command("agentdojo")
def agentdojo_command(
    runs: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="AgentDojo runs/ directory.")
    ],
    ground_truth: Annotated[
        Path, typer.Option(exists=True, dir_okay=False, help="ground_truth.json path.")
    ],
    out: Annotated[Path, typer.Option(help="Output directory.")],
    suites: Annotated[
        str | None, typer.Option(help="Comma-separated suite names. Default: all.")
    ] = None,
    models: Annotated[
        str | None, typer.Option(help="Comma-separated model/pipeline names. Default: all.")
    ] = None,
) -> None:
    """Parse AgentDojo traces under ``--runs`` into ``<out>/agentdojo.jsonl`` plus a manifest."""
    suite_list = [s.strip() for s in suites.split(",")] if suites else None
    model_list = [m.strip() for m in models.split(",")] if models else None
    gt = load_ground_truth(ground_truth)

    examples = []
    per_dimension: dict[RiskDimension, Counter[str]] = {d: Counter() for d in RiskDimension}
    per_attack_type: Counter[str] = Counter()
    prompt_injection_yes_calls = 0
    security_true_runs: set[str] = set()

    for path in iter_trace_files(runs, suites=suite_list, models=model_list):
        trace = parse_trace(path)
        if not trace.suite_name or not trace.proposed_calls:
            continue
        overlay = overlay_identity(trace.suite_name, trace, gt)
        if trace.injection_task_id is not None and trace.security:
            security_true_runs.add(str(path))
        for call in trace.proposed_calls:
            labels = label_call(call, trace, gt)
            example = to_example(call, trace, overlay, labels)
            examples.append(example)
            per_attack_type[trace.attack_type or "none"] += 1
            for dimension, value in labels.values.items():
                per_dimension[dimension][value.value] += 1
            if labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.YES:
                prompt_injection_yes_calls += 1

    out.mkdir(parents=True, exist_ok=True)
    out_path = out / "agentdojo.jsonl"
    write_jsonl(out_path, examples)

    manifest = {
        "n_examples": len(examples),
        "per_dimension": {d.value: dict(per_dimension[d]) for d in RiskDimension},
        "per_attack_type": dict(per_attack_type),
        "prompt_injection_yes_calls": prompt_injection_yes_calls,
        "security_true_runs": len(security_true_runs),
    }
    (out / "agentdojo_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    typer.echo(_render_table(manifest))
    typer.echo(f"wrote {len(examples)} examples -> {out_path}")
