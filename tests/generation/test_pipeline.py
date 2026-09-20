from __future__ import annotations

from pathlib import Path

import pytest

from forecheck.contracts import ContrastiveAxis
from forecheck.generation.pipeline import (
    GenerationPipeline,
    GenerationProgress,
    OfflineViolationError,
    PipelineConfig,
    ScenarioJob,
    TokenBucket,
    compute_example_id,
    derive_seed,
    make_pair_jobs,
)
from forecheck.generation.renderers import LLMRenderer, OfflineTemplateRenderer
from tests.data.factories import make_latent


def _no_sleep(_seconds: float) -> None:
    return None


def test_derive_seed_is_deterministic() -> None:
    assert derive_seed(1, "scenario-a") == derive_seed(1, "scenario-a")
    assert derive_seed(1, "scenario-a") != derive_seed(1, "scenario-b")
    assert derive_seed(1, "scenario-a") != derive_seed(2, "scenario-a")


def test_compute_example_id_is_stable_and_input_sensitive() -> None:
    base_id = compute_example_id(
        family_id="fam",
        scenario_id="s1",
        transformation=None,
        renderer_name="r",
        renderer_version="1",
    )
    assert base_id == compute_example_id(
        family_id="fam",
        scenario_id="s1",
        transformation=None,
        renderer_name="r",
        renderer_version="1",
    )
    other_id = compute_example_id(
        family_id="fam",
        scenario_id="s2",
        transformation=None,
        renderer_name="r",
        renderer_version="1",
    )
    assert base_id != other_id


def test_pipeline_generates_examples_offline(tmp_path: Path) -> None:
    config = PipelineConfig(
        master_seed=1, output_path=tmp_path / "out.jsonl", cache_dir=tmp_path / "cache"
    )
    pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    jobs = [
        ScenarioJob(latent=make_latent(scenario_id=f"s-{i}", family_id=f"fam-{i}"))
        for i in range(5)
    ]
    examples = pipeline.run(jobs, OfflineTemplateRenderer())
    assert len(examples) == 5
    assert config.output_path.exists()
    assert pipeline.total_cost_usd == 0.0


def test_pipeline_offline_rejects_network_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    config = PipelineConfig(master_seed=1, output_path=tmp_path / "out.jsonl", offline=True)
    pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    renderer = LLMRenderer(chat_fn=lambda _p: "{}")
    with pytest.raises(OfflineViolationError):
        pipeline.run([ScenarioJob(latent=make_latent())], renderer)


def test_pipeline_is_resumable(tmp_path: Path) -> None:
    output_path = tmp_path / "out.jsonl"
    config = PipelineConfig(master_seed=1, output_path=output_path, cache_dir=tmp_path / "cache")
    jobs = [
        ScenarioJob(latent=make_latent(scenario_id=f"s-{i}", family_id=f"fam-{i}"))
        for i in range(3)
    ]

    first_pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    first_batch = first_pipeline.run(jobs, OfflineTemplateRenderer())
    assert len(first_batch) == 3

    second_pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    second_batch = second_pipeline.run(jobs, OfflineTemplateRenderer())
    assert second_batch == []

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_pipeline_uses_cache_on_second_run_with_fresh_output(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    jobs = [ScenarioJob(latent=make_latent(scenario_id="s-1", family_id="fam-1"))]

    config_a = PipelineConfig(master_seed=1, output_path=tmp_path / "a.jsonl", cache_dir=cache_dir)
    GenerationPipeline(config_a, sleep_fn=_no_sleep).run(jobs, OfflineTemplateRenderer())

    hits: list[GenerationProgress] = []
    config_b = PipelineConfig(master_seed=1, output_path=tmp_path / "b.jsonl", cache_dir=cache_dir)
    GenerationPipeline(config_b, sleep_fn=_no_sleep).run(
        jobs, OfflineTemplateRenderer(), progress_cb=hits.append
    )
    assert hits[-1].cached == 1


def test_pipeline_retries_then_succeeds(tmp_path: Path) -> None:
    config = PipelineConfig(
        master_seed=1,
        output_path=tmp_path / "out.jsonl",
        cache_dir=tmp_path / "cache",
        base_backoff_s=0.001,
    )
    sleeps: list[float] = []
    pipeline = GenerationPipeline(config, sleep_fn=sleeps.append)

    attempts = {"n": 0}

    class FlakyRenderer:
        name = "flaky"
        version = "1.0.0"
        requires_network = False

        def render(self, latent: object, rng: object) -> object:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("transient failure")
            return OfflineTemplateRenderer().render(latent, rng)  # type: ignore[arg-type]

    examples = pipeline.run([ScenarioJob(latent=make_latent())], FlakyRenderer())
    assert len(examples) == 1
    assert attempts["n"] == 3
    assert len(sleeps) == 2


def test_pipeline_raises_after_exhausting_retries(tmp_path: Path) -> None:
    config = PipelineConfig(
        master_seed=1,
        output_path=tmp_path / "out.jsonl",
        cache_dir=tmp_path / "cache",
        base_backoff_s=0.001,
        max_retries=2,
    )
    pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)

    class AlwaysFailsRenderer:
        name = "broken"
        version = "1.0.0"
        requires_network = False

        def render(self, latent: object, rng: object) -> object:
            raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        pipeline.run([ScenarioJob(latent=make_latent())], AlwaysFailsRenderer())


def test_token_bucket_waits_when_exhausted() -> None:
    clock = {"t": 0.0}
    bucket = TokenBucket(rate_per_s=1.0, burst=1.0, clock_fn=lambda: clock["t"])
    waits: list[float] = []
    bucket.acquire(waits.append)
    bucket.acquire(waits.append)
    assert waits == [1.0]


def test_pipeline_accumulates_cost(tmp_path: Path) -> None:
    config = PipelineConfig(
        master_seed=1,
        output_path=tmp_path / "out.jsonl",
        cache_dir=tmp_path / "cache",
        cost_fn=lambda _latent, _context: 0.02,
    )
    pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    jobs = [
        ScenarioJob(latent=make_latent(scenario_id=f"s-{i}", family_id=f"fam-{i}"))
        for i in range(3)
    ]
    examples = pipeline.run(jobs, OfflineTemplateRenderer())
    assert pipeline.total_cost_usd == pytest.approx(0.06)
    assert all(e.provenance.cost_usd == pytest.approx(0.02) for e in examples)


def test_pipeline_tags_contrastive_rows(tmp_path: Path) -> None:
    config = PipelineConfig(
        master_seed=1, output_path=tmp_path / "out.jsonl", cache_dir=tmp_path / "cache"
    )
    pipeline = GenerationPipeline(config, sleep_fn=_no_sleep)
    base = make_latent(scenario_id="base", family_id="fam")
    renderer = OfflineTemplateRenderer()
    base_job, derived_job = make_pair_jobs(
        base,
        ContrastiveAxis.RESOURCE_SENSITIVITY,
        renderer_name=renderer.name,
        renderer_version=renderer.version,
        from_value="internal",
        to_value="restricted",
    )
    examples = pipeline.run([base_job, derived_job], renderer)
    paired = [e for e in examples if e.contrastive_pair_id is not None]
    assert len(paired) == 2
    assert paired[0].contrastive_pair_id == paired[1].contrastive_pair_id
    derived = [e for e in paired if e.transformation is not None]
    assert len(derived) == 1
    assert derived[0].transformation is not None
    assert derived[0].transformation.base_example_id == paired[0].example_id
