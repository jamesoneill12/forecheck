"""Runs the LLM judge over a sample: one chat call per example, strict JSON parsing with
one retry on failure, and a jsonl cache keyed by ``(model, example_id, strip_identity)``
so repeated invocations over the same ``--out`` file are idempotent.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.judge.dimensions import build_system_prompt
from forecheck.judge.providers import JudgeProvider, estimate_cost_usd, provider_for_name
from forecheck.judge.schema import JudgeDimensionVerdict, JudgeLabelRow, JudgeSampleRow

__all__ = [
    "LabelRunResult",
    "label_examples",
    "load_label_cache",
    "write_label_rows",
]


def load_label_cache(path: Path) -> dict[tuple[str, str, bool], JudgeLabelRow]:
    """Load a previously written ``--out`` jsonl as a cache keyed by
    :attr:`JudgeLabelRow.cache_key`."""
    if not path.exists():
        return {}
    cache: dict[tuple[str, str, bool], JudgeLabelRow] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                row = JudgeLabelRow.model_validate_json(stripped)
                cache[row.cache_key] = row
    return cache


def write_label_rows(path: Path, rows: Sequence[JudgeLabelRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row.model_dump_json())
            handle.write("\n")


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_verdicts(text: str) -> dict[RiskDimension, JudgeDimensionVerdict] | None:
    try:
        payload = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    verdicts: dict[RiskDimension, JudgeDimensionVerdict] = {}
    for dimension in RiskDimension:
        entry = payload.get(dimension.value)
        if not isinstance(entry, dict):
            return None
        value = entry.get("value")
        if value not in ("yes", "no", "not_applicable"):
            return None
        rationale = entry.get("rationale", "")
        verdicts[dimension] = JudgeDimensionVerdict(
            value=LabelValue(value), rationale=str(rationale)
        )
    return verdicts


def _label_one(
    row: JudgeSampleRow,
    provider: JudgeProvider,
    provider_name: str,
    system_prompt: str,
    client: httpx.Client,
    *,
    strip_identity: bool,
) -> JudgeLabelRow:
    user_text = row.rendered_stripped if strip_identity else row.rendered_full
    response = provider.complete(system=system_prompt, user=user_text, client=client)
    verdicts = _parse_verdicts(response.text)
    raw_completion = response.text
    input_tokens = response.input_tokens
    output_tokens = response.output_tokens
    retried = False
    if verdicts is None:
        retried = True
        retry_response = provider.complete(system=system_prompt, user=user_text, client=client)
        raw_completion = retry_response.text
        input_tokens += retry_response.input_tokens
        output_tokens += retry_response.output_tokens
        verdicts = _parse_verdicts(retry_response.text)
    parse_ok = verdicts is not None
    labels: dict[RiskDimension, JudgeDimensionVerdict | None] = (
        dict(verdicts) if verdicts is not None else dict.fromkeys(RiskDimension, None)
    )
    return JudgeLabelRow(
        example_id=row.example_id,
        model=provider.model,
        provider=provider_name,
        strip_identity=strip_identity,
        labels=labels,
        parse_ok=parse_ok,
        retried=retried,
        raw_completion=raw_completion,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_cost_usd(provider.model, input_tokens, output_tokens),
        created_at=datetime.now(UTC),
        error=None if parse_ok else "judge output did not parse as the required JSON schema",
    )


@dataclass(frozen=True, slots=True)
class LabelRunResult:
    rows: list[JudgeLabelRow]
    new_rows: list[JudgeLabelRow]


def label_examples(
    rows: Sequence[JudgeSampleRow],
    *,
    provider_name: str,
    model: str,
    strip_identity: bool = False,
    concurrency: int = 8,
    cache: dict[tuple[str, str, bool], JudgeLabelRow] | None = None,
    provider: JudgeProvider | None = None,
) -> LabelRunResult:
    """Label every row in ``rows``, reusing ``cache`` and calling ``provider`` for the rest."""
    active_provider = provider if provider is not None else provider_for_name(provider_name, model)
    system_prompt = build_system_prompt()

    cached_rows: list[JudgeLabelRow] = []
    to_run: list[JudgeSampleRow] = []
    for row in rows:
        key = (active_provider.model, row.example_id, strip_identity)
        cached = cache.get(key) if cache is not None else None
        if cached is not None:
            cached_rows.append(cached)
        else:
            to_run.append(row)

    new_rows: list[JudgeLabelRow] = []
    if to_run:
        with httpx.Client() as client:

            def _run(sample_row: JudgeSampleRow) -> JudgeLabelRow:
                return _label_one(
                    sample_row,
                    active_provider,
                    provider_name,
                    system_prompt,
                    client,
                    strip_identity=strip_identity,
                )

            with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
                new_rows = list(pool.map(_run, to_run))

    by_id = {r.example_id: r for r in cached_rows + new_rows}
    ordered = [by_id[row.example_id] for row in rows]
    return LabelRunResult(rows=ordered, new_rows=new_rows)
