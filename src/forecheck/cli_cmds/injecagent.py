"""``forecheck external injecagent`` — port InjecAgent test cases to forecheck Examples."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from forecheck.contracts import RiskDimension
from forecheck.data.io import write_jsonl
from forecheck.external.injecagent import (
    iter_examples,
    load_cases,
    load_simulated_responses,
    load_tools,
)

__all__ = ["injecagent_command"]


def _render_table(manifest: dict) -> str:
    lines = [f"examples: {manifest['n_examples']}", "", "cases per type:"]
    for case_type, n in sorted(manifest["cases_per_type"].items()):
        lines.append(f"  {case_type}: {n}")
    lines.append("")
    lines.append("label counts per dimension:")
    for dimension, counts in manifest["per_dimension"].items():
        counted = ", ".join(f"{value}={n}" for value, n in counts.items() if n)
        lines.append(f"  {dimension}: {counted}")
    return "\n".join(lines)


def injecagent_command(
    data: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="InjecAgent data/ directory.")
    ],
    out: Annotated[Path, typer.Option(help="Output directory.")],
) -> None:
    """Parse InjecAgent cases under ``--data`` into ``<out>/injecagent.jsonl`` plus a manifest."""
    tools = load_tools(data / "tools.json")
    sim_responses = load_simulated_responses(data / "attacker_simulated_responses.json")
    dh_cases = load_cases(data / "test_cases_dh_base.json", "dh")
    ds_cases = load_cases(data / "test_cases_ds_base.json", "ds")
    cases = dh_cases + ds_cases

    examples = list(iter_examples(cases, tools, sim_responses))

    per_dimension: dict[RiskDimension, Counter[str]] = {d: Counter() for d in RiskDimension}
    for example in examples:
        for dimension, value in example.labels.values.items():
            per_dimension[dimension][value.value] += 1

    out.mkdir(parents=True, exist_ok=True)
    out_path = out / "injecagent.jsonl"
    write_jsonl(out_path, examples)

    manifest = {
        "n_examples": len(examples),
        "cases_per_type": {"dh": len(dh_cases), "ds": len(ds_cases)},
        "per_dimension": {d.value: dict(per_dimension[d]) for d in RiskDimension},
    }
    (out / "injecagent_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    typer.echo(_render_table(manifest))
    typer.echo(f"wrote {len(examples)} examples -> {out_path}")
