from __future__ import annotations

import json
from pathlib import Path

import httpx

from forecheck.contracts import DifficultyTier, LabelValue, RiskDimension, Split
from forecheck.judge.labeling import label_examples, load_label_cache, write_label_rows
from forecheck.judge.providers import ProviderResponse
from forecheck.judge.schema import JudgeSampleRow


def _sample_row(example_id: str = "ex-1") -> JudgeSampleRow:
    return JudgeSampleRow(
        example_id=example_id,
        family_id=f"{example_id}-fam",
        split=Split.TEST,
        tool_family=None,
        policy_kinds=(),
        difficulty=DifficultyTier.MEDIUM,
        rendered_full="full text",
        rendered_stripped="stripped text",
        generator_labels=dict.fromkeys(RiskDimension, LabelValue.NO),
    )


def _valid_completion() -> str:
    return json.dumps({d.value: {"value": "no", "rationale": "ok"} for d in RiskDimension})


class _ScriptedProvider:
    model = "fake-model-v1"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse:
        text = self._responses[self.calls]
        self.calls += 1
        return ProviderResponse(text=text, input_tokens=100, output_tokens=20)


def test_label_examples_parses_a_valid_completion_on_the_first_try() -> None:
    provider = _ScriptedProvider([_valid_completion()])
    result = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    row = result.rows[0]
    assert row.parse_ok is True
    assert row.retried is False
    assert row.labels[RiskDimension.FINANCIAL_COMMITMENT] is not None
    assert row.labels[RiskDimension.FINANCIAL_COMMITMENT].value == LabelValue.NO
    assert provider.calls == 1


def test_label_examples_retries_once_on_parse_failure_then_succeeds() -> None:
    provider = _ScriptedProvider(["not json at all", _valid_completion()])
    result = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    row = result.rows[0]
    assert row.parse_ok is True
    assert row.retried is True
    assert provider.calls == 2


def test_label_examples_records_failure_after_retry_is_exhausted() -> None:
    provider = _ScriptedProvider(["nope", "still nope"])
    result = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    row = result.rows[0]
    assert row.parse_ok is False
    assert row.retried is True
    assert row.error is not None
    assert all(v is None for v in row.labels.values())
    assert provider.calls == 2


def test_label_examples_rejects_a_completion_missing_a_dimension() -> None:
    incomplete = {d.value: {"value": "no", "rationale": "ok"} for d in list(RiskDimension)[:-1]}
    provider = _ScriptedProvider([json.dumps(incomplete), _valid_completion()])
    result = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    assert result.rows[0].retried is True
    assert result.rows[0].parse_ok is True


def test_label_examples_reuses_cache_and_skips_the_provider_call() -> None:
    provider = _ScriptedProvider([_valid_completion()])
    first = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    assert provider.calls == 1
    cache = {r.cache_key: r for r in first.rows}

    second = label_examples(
        [_sample_row()],
        provider_name="openai_compat",
        model=provider.model,
        provider=provider,
        cache=cache,
    )

    assert provider.calls == 1
    assert len(second.new_rows) == 0
    assert second.rows[0].example_id == "ex-1"


def test_label_examples_cache_key_is_specific_to_strip_identity() -> None:
    provider = _ScriptedProvider([_valid_completion(), _valid_completion()])
    first = label_examples(
        [_sample_row()],
        provider_name="openai_compat",
        model=provider.model,
        provider=provider,
        strip_identity=False,
    )
    cache = {r.cache_key: r for r in first.rows}
    second = label_examples(
        [_sample_row()],
        provider_name="openai_compat",
        model=provider.model,
        provider=provider,
        strip_identity=True,
        cache=cache,
    )
    assert provider.calls == 2
    assert len(second.new_rows) == 1


def test_write_then_load_label_cache_round_trips_and_reruns_are_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "labels.jsonl"
    provider = _ScriptedProvider([_valid_completion()])
    result = label_examples(
        [_sample_row()], provider_name="openai_compat", model=provider.model, provider=provider
    )
    write_label_rows(out, result.rows)

    cache = load_label_cache(out)
    assert len(cache) == 1

    rerun_provider = _ScriptedProvider([_valid_completion()])
    rerun = label_examples(
        [_sample_row()],
        provider_name="openai_compat",
        model=rerun_provider.model,
        provider=rerun_provider,
        cache=cache,
    )
    write_label_rows(out, rerun.rows)

    assert rerun_provider.calls == 0
    reloaded = load_label_cache(out)
    assert len(reloaded) == 1
    assert reloaded[next(iter(reloaded))].example_id == "ex-1"


def test_provider_exception_becomes_error_row_and_is_not_cached(tmp_path):
    from forecheck.judge.labeling import label_examples, load_label_cache, write_label_rows
    from forecheck.judge.schema import JudgeSampleRow

    class Boom:
        model = "m"

        def complete(self, *, system, user, client):
            raise RuntimeError("codex CLI timed out after 600.0s")

    row = JudgeSampleRow(
        example_id="e1",
        family_id="f",
        split="test",
        tool_family="mcp",
        policy_kinds=[],
        difficulty="easy",
        rendered_full="x",
        rendered_stripped="x",
        generator_labels={},
    )
    result = label_examples([row], provider_name="codex_cli", model="m", provider=Boom())
    assert result.rows[0].parse_ok is False
    assert result.rows[0].error.startswith("provider error")
    out = tmp_path / "labels.jsonl"
    write_label_rows(out, result.rows)
    assert load_label_cache(out) == {}
