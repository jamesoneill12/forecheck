"""Declarative configuration for the ``forecheck data generate`` CLI command.

A :class:`GenerationConfig` fully determines the job list a run produces: which tool
families to draw bulk scenarios from, how many per family, how many contrastive pairs
per axis, the master seed, and an optional target difficulty mix. Everything else
(rendering, labeling, id derivation) is the existing :mod:`forecheck.generation.pipeline`.
"""

from __future__ import annotations

import random
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from forecheck.contracts import ContrastiveAxis, DifficultyTier, LatentScenario, ToolFamily
from forecheck.data.contrastive import make_pair
from forecheck.generation.pipeline import ScenarioJob, derive_seed, make_pair_jobs
from forecheck.generation.renderers import OfflineTemplateRenderer
from forecheck.generation.scenarios import iter_scenarios, sample_scenario

__all__ = ["GenerationConfig", "build_jobs", "load_generation_config"]

_MAX_PAIR_BASE_ATTEMPTS = 25
_MAX_DIFFICULTY_ATTEMPTS_PER_SLOT = 50


class GenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int
    families: list[ToolFamily] = Field(default_factory=lambda: list(ToolFamily))
    n_per_family: int = Field(gt=0)
    pairs_per_axis: int = Field(default=1, ge=0)
    difficulty_mix: dict[DifficultyTier, float] | None = Field(
        default=None,
        description="Optional target share per difficulty tier for the bulk scenarios "
        "(must sum to 1.0). Best-effort: achieved by rejection sampling, bounded by "
        f"{_MAX_DIFFICULTY_ATTEMPTS_PER_SLOT} draws per slot.",
    )

    @model_validator(mode="after")
    def _difficulty_mix_sums_to_one(self) -> GenerationConfig:
        if self.difficulty_mix is not None:
            total = sum(self.difficulty_mix.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"difficulty_mix must sum to 1.0, got {total}")
        return self


def load_generation_config(path: Path, *, seed_override: int | None = None) -> GenerationConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"generation config {path} did not parse to a mapping")
    if seed_override is not None:
        raw = {**raw, "seed": seed_override}
    return GenerationConfig.model_validate(raw)


def _bulk_scenarios_for_mix(
    rng: random.Random, family: ToolFamily, n: int, mix: dict[DifficultyTier, float]
) -> list[LatentScenario]:
    targets: dict[DifficultyTier, int] = {tier: round(n * frac) for tier, frac in mix.items()}
    counts: dict[DifficultyTier, int] = dict.fromkeys(DifficultyTier, 0)
    selected: list[LatentScenario] = []
    for slot in range(n):
        for _attempt in range(_MAX_DIFFICULTY_ATTEMPTS_PER_SLOT):
            candidate = sample_scenario(
                rng, family, f"{family.value}-mix-{slot:05d}-{_attempt:03d}"
            )
            if counts[candidate.difficulty] < targets.get(candidate.difficulty, 0):
                counts[candidate.difficulty] += 1
                selected.append(candidate)
                break
        else:
            selected.append(candidate)
            counts[candidate.difficulty] += 1
    return selected


def _bulk_jobs(config: GenerationConfig) -> list[ScenarioJob]:
    rng = random.Random(config.seed)  # noqa: S311
    if config.difficulty_mix is None:
        scenarios = iter_scenarios(
            rng, families=tuple(config.families), n_per_family=config.n_per_family
        )
        return [ScenarioJob(latent=latent) for latent in scenarios]

    scenarios = []
    for family in config.families:
        scenarios.extend(
            _bulk_scenarios_for_mix(rng, family, config.n_per_family, config.difficulty_mix)
        )
    return [ScenarioJob(latent=latent) for latent in scenarios]


def _sample_valid_pair_base(
    rng: random.Random, family: ToolFamily, axis: ContrastiveAxis, scenario_id: str
) -> LatentScenario:
    """Sample a base scenario for which flipping ``axis`` yields a valid scenario."""
    last_error: ValidationError | None = None
    for attempt in range(_MAX_PAIR_BASE_ATTEMPTS):
        base = sample_scenario(rng, family, f"{scenario_id}-{attempt:02d}")
        try:
            flipped = make_pair(base, axis)
            LatentScenario.model_validate(flipped.model_dump())
        except ValidationError as exc:
            last_error = exc
            continue
        return base
    raise RuntimeError(
        f"could not sample a base scenario compatible with axis {axis.value!r} in family "
        f"{family.value!r} after {_MAX_PAIR_BASE_ATTEMPTS} attempts"
    ) from last_error


def _pair_jobs(config: GenerationConfig) -> list[ScenarioJob]:
    if config.pairs_per_axis == 0:
        return []
    renderer_name = OfflineTemplateRenderer().name
    renderer_version = OfflineTemplateRenderer().version
    jobs: list[ScenarioJob] = []
    for axis in ContrastiveAxis:
        for i in range(config.pairs_per_axis):
            seed = derive_seed(config.seed, f"pair:{axis.value}:{i}")
            rng = random.Random(seed)  # noqa: S311
            family = config.families[i % len(config.families)]
            base = _sample_valid_pair_base(rng, family, axis, f"pair-{axis.value}-{i:03d}")
            base_job, derived_job = make_pair_jobs(
                base,
                axis,
                renderer_name=renderer_name,
                renderer_version=renderer_version,
                from_value="base",
                to_value="flipped",
            )
            jobs.append(base_job)
            jobs.append(derived_job)
    return jobs


def build_jobs(config: GenerationConfig) -> list[ScenarioJob]:
    """Build the full job list (bulk scenarios plus contrastive pairs) for ``config``."""
    return [*_bulk_jobs(config), *_pair_jobs(config)]
