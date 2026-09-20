"""Generation orchestration: seeding, caching, retries, cost, resumability, rate limits.

The pipeline never prints; progress is reported through an injected callback so it can
run silently in a test or a batch job alike. Every side effect that would otherwise be
nondeterministic in a test (sleeping, wall-clock time) is behind an injectable hook.
"""

from __future__ import annotations

import hashlib
import random
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from forecheck.contracts import (
    ActionContext,
    ContrastiveAxis,
    Example,
    LatentScenario,
    Provenance,
    Transformation,
)
from forecheck.data.contrastive import contrastive_pair_id, make_pair
from forecheck.data.io import read_jsonl
from forecheck.data.labeling import derive_labels
from forecheck.generation.renderers import Renderer

__all__ = [
    "GenerationPipeline",
    "GenerationProgress",
    "OfflineViolationError",
    "PipelineConfig",
    "ScenarioJob",
    "TokenBucket",
    "compute_example_id",
    "derive_seed",
    "make_pair_jobs",
]


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


_new_random = random.Random


class OfflineViolationError(RuntimeError):
    """Raised when an offline pipeline is asked to use a network-requiring renderer."""


def derive_seed(master_seed: int, scenario_id: str) -> int:
    """Derive a per-scenario seed deterministically from the master seed."""
    digest = hashlib.sha256(f"{master_seed}:{scenario_id}".encode()).hexdigest()
    return int(digest[:16], 16)


def compute_example_id(
    *,
    family_id: str,
    scenario_id: str,
    transformation: Transformation | None,
    renderer_name: str,
    renderer_version: str,
) -> str:
    """A stable id derived from (family, scenario, transformation, renderer identity)."""
    axis = transformation.axis.value if transformation is not None else "base"
    base_id = transformation.base_example_id if transformation is not None else ""
    key = f"{family_id}|{scenario_id}|{axis}|{base_id}|{renderer_name}|{renderer_version}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


@dataclass(frozen=True)
class ScenarioJob:
    """One unit of generation work: a latent scenario, optionally a contrastive row."""

    latent: LatentScenario
    transformation: Transformation | None = None
    contrastive_pair_id: str | None = None


def make_pair_jobs(
    base: LatentScenario,
    axis: ContrastiveAxis,
    *,
    renderer_name: str,
    renderer_version: str,
    from_value: str,
    to_value: str,
) -> tuple[ScenarioJob, ScenarioJob]:
    """Build the linked (base, derived) job pair for one contrastive axis.

    Both jobs carry the same ``contrastive_pair_id`` so a pair is identifiable from
    either half, not only by following the derived row's ``transformation.base_example_id``.
    """
    flipped = make_pair(base, axis)
    base_id = compute_example_id(
        family_id=base.family_id,
        scenario_id=base.scenario_id,
        transformation=None,
        renderer_name=renderer_name,
        renderer_version=renderer_version,
    )
    pair_id = contrastive_pair_id(base.scenario_id, axis)
    transformation = Transformation(
        axis=axis, base_example_id=base_id, from_value=from_value, to_value=to_value
    )
    base_job = ScenarioJob(latent=base, contrastive_pair_id=pair_id)
    derived_job = ScenarioJob(
        latent=flipped, transformation=transformation, contrastive_pair_id=pair_id
    )
    return base_job, derived_job


@dataclass(frozen=True)
class GenerationProgress:
    completed: int
    total: int
    cached: int
    resumed_skipped: int
    errors: int


@dataclass(frozen=True)
class PipelineConfig:
    master_seed: int
    output_path: Path
    offline: bool = True
    max_retries: int = 5
    base_backoff_s: float = 0.05
    rate_limit_per_s: float = 50.0
    rate_limit_burst: float = 10.0
    cache_dir: Path = field(default_factory=lambda: Path(".cache/generation"))
    generator_name: str = "forecheck-synthetic"
    generator_version: str = "1.0.0"
    cost_fn: Callable[[LatentScenario, ActionContext], float] | None = None


class TokenBucket:
    """Minimal token-bucket rate limiter with an injectable clock."""

    def __init__(self, rate_per_s: float, burst: float, *, clock_fn: Callable[[], float]) -> None:
        self._rate = rate_per_s
        self._capacity = burst
        self._tokens = burst
        self._clock_fn = clock_fn
        self._last = clock_fn()

    def acquire(self, sleep_fn: Callable[[float], None]) -> None:
        now = self._clock_fn()
        self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if self._tokens < 1.0:
            wait_s = (1.0 - self._tokens) / self._rate
            sleep_fn(wait_s)
            self._tokens = 0.0
            self._last = self._clock_fn()
        else:
            self._tokens -= 1.0


def _append_jsonl(path: Path, examples: Iterable[Example]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for example in examples:
            handle.write(example.model_dump_json())
            handle.write("\n")


class GenerationPipeline:
    """Drives a :class:`Renderer` over a batch of :class:`ScenarioJob` items."""

    def __init__(
        self,
        config: PipelineConfig,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.config = config
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn
        self._now_fn = now_fn
        self._total_cost_usd = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost_usd

    def _load_existing_ids(self) -> set[str]:
        if not self.config.output_path.exists():
            return set()
        return {example.example_id for example in read_jsonl(self.config.output_path)}

    def _cache_key(self, latent: LatentScenario, renderer: Renderer) -> str:
        payload = f"{latent.model_dump_json()}|{renderer.name}|{renderer.version}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.config.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> ActionContext | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        return ActionContext.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_cache(self, key: str, context: ActionContext) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(context.model_dump_json(), encoding="utf-8")

    def _render_with_retry(
        self, renderer: Renderer, latent: LatentScenario, rng: random.Random, seed: int
    ) -> ActionContext:
        jitter_rng = _new_random(seed ^ 0x5EED5EED)
        attempt = 0
        while True:
            try:
                return renderer.render(latent, rng)
            except Exception:
                attempt += 1
                if attempt > self.config.max_retries:
                    raise
                backoff = self.config.base_backoff_s * (2 ** (attempt - 1))
                jitter = jitter_rng.uniform(0.0, backoff * 0.1)
                self._sleep_fn(backoff + jitter)

    def run(
        self,
        jobs: Sequence[ScenarioJob],
        renderer: Renderer,
        *,
        progress_cb: Callable[[GenerationProgress], None] | None = None,
    ) -> list[Example]:
        if self.config.offline and renderer.requires_network:
            raise OfflineViolationError(
                f"renderer {renderer.name!r} requires network access but the pipeline "
                "is configured offline=True"
            )

        existing_ids = self._load_existing_ids()
        bucket = TokenBucket(
            self.config.rate_limit_per_s, self.config.rate_limit_burst, clock_fn=self._clock_fn
        )
        results: list[Example] = []
        completed = 0
        cached = 0
        resumed_skipped = 0
        errors = 0

        for job in jobs:
            example_id = compute_example_id(
                family_id=job.latent.family_id,
                scenario_id=job.latent.scenario_id,
                transformation=job.transformation,
                renderer_name=renderer.name,
                renderer_version=renderer.version,
            )
            if example_id in existing_ids:
                resumed_skipped += 1
                continue

            seed = derive_seed(self.config.master_seed, job.latent.scenario_id)
            cache_key = self._cache_key(job.latent, renderer)
            context = self._read_cache(cache_key)
            if context is not None:
                cached += 1
            else:
                bucket.acquire(self._sleep_fn)
                try:
                    context = self._render_with_retry(renderer, job.latent, _new_random(seed), seed)
                except Exception:
                    errors += 1
                    raise
                self._write_cache(cache_key, context)

            cost = 0.0 if self.config.cost_fn is None else self.config.cost_fn(job.latent, context)
            self._total_cost_usd += cost

            example = Example(
                example_id=example_id,
                family_id=job.latent.family_id,
                latent=job.latent,
                context=context,
                labels=derive_labels(job.latent),
                provenance=Provenance(
                    generator_name=self.config.generator_name,
                    generator_version=self.config.generator_version,
                    renderer=renderer.name,
                    renderer_version=renderer.version,
                    seed=seed,
                    created_at=self._now_fn(),
                    cost_usd=cost,
                ),
                contrastive_pair_id=job.contrastive_pair_id,
                transformation=job.transformation,
                difficulty=job.latent.difficulty,
                tool_family=job.latent.tool.family,
            )
            results.append(example)
            _append_jsonl(self.config.output_path, [example])
            existing_ids.add(example_id)
            completed += 1

            if progress_cb is not None:
                progress_cb(
                    GenerationProgress(
                        completed=completed,
                        total=len(jobs),
                        cached=cached,
                        resumed_skipped=resumed_skipped,
                        errors=errors,
                    )
                )

        return results
