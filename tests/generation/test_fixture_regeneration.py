"""Regenerating the fixture dataset from the same seed must be exactly reproducible.

This exercises the identical code path documented in ``data/fixtures/README.md``
(``iter_scenarios`` -> ``GenerationPipeline`` -> ``OfflineTemplateRenderer``) at a small
scale, so the test stays fast while still covering the reproducibility guarantee the
real fixture regeneration depends on.
"""

from __future__ import annotations

import random
from pathlib import Path

from forecheck.contracts import ToolFamily
from forecheck.generation.pipeline import GenerationPipeline, PipelineConfig, ScenarioJob
from forecheck.generation.renderers import OfflineTemplateRenderer
from forecheck.generation.scenarios import iter_scenarios

_SEED = 424242
_FAMILIES = (ToolFamily.EMAIL_MESSAGING, ToolFamily.CLOUD_ADMIN)
_N_PER_FAMILY = 4


def _generate(tmp_path: Path, run_name: str) -> list[tuple[str, dict[str, str]]]:
    rng = random.Random(_SEED)
    scenarios = iter_scenarios(rng, families=_FAMILIES, n_per_family=_N_PER_FAMILY)
    jobs = [ScenarioJob(latent=latent) for latent in scenarios]
    config = PipelineConfig(
        master_seed=_SEED,
        output_path=tmp_path / f"{run_name}.jsonl",
        cache_dir=tmp_path / f"{run_name}-cache",
    )
    pipeline = GenerationPipeline(config)
    examples = pipeline.run(jobs, OfflineTemplateRenderer())
    return [(e.example_id, dict(e.labels.values)) for e in examples]


def test_regeneration_from_same_seed_reproduces_ids_and_labels(tmp_path: Path) -> None:
    first = _generate(tmp_path, "run-a")
    second = _generate(tmp_path, "run-b")
    assert first == second
    assert len(first) == len(_FAMILIES) * _N_PER_FAMILY
