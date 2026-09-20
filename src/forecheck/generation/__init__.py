"""Synthetic scenario sampling and generation orchestration."""

from __future__ import annotations

from forecheck.generation.config import GenerationConfig, build_jobs, load_generation_config
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
from forecheck.generation.renderers import LLMRenderer, OfflineTemplateRenderer, Renderer
from forecheck.generation.scenarios import iter_scenarios, sample_scenario

__all__ = [
    "GenerationConfig",
    "GenerationPipeline",
    "GenerationProgress",
    "LLMRenderer",
    "OfflineTemplateRenderer",
    "OfflineViolationError",
    "PipelineConfig",
    "Renderer",
    "ScenarioJob",
    "TokenBucket",
    "build_jobs",
    "compute_example_id",
    "derive_seed",
    "iter_scenarios",
    "load_generation_config",
    "make_pair_jobs",
    "sample_scenario",
]
