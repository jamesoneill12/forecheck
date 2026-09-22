"""Dataset generation must be byte-identical for a fixed seed, independent of the
per-process string-hash seed.

A prior bug converted the ``ATTACK_SEQUENCE_PATTERNS`` frozenset (of ``StrEnum``
members, i.e. hash-randomized strings) straight into a tuple consumed by
``rng.choice`` in :func:`forecheck.generation.scenarios._sample_sequence`, so
``sequence_pattern`` (and the trajectory text derived from it) differed between two
otherwise-identical runs whenever they landed in separate Python processes with
different ``PYTHONHASHSEED`` values -- exactly what happens running the CLI twice.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

_GENERATE_SCRIPT = """
import sys
from datetime import UTC, datetime
from pathlib import Path

from forecheck.generation.config import GenerationConfig, build_jobs
from forecheck.generation.pipeline import GenerationPipeline, PipelineConfig
from forecheck.generation.renderers import OfflineTemplateRenderer

out_path = Path(sys.argv[1])
config = GenerationConfig(
    seed=13579,
    families=["email_messaging", "cloud_admin"],
    n_per_family=40,
    pairs_per_axis=1,
)
jobs = build_jobs(config)
pipeline_config = PipelineConfig(
    master_seed=config.seed, output_path=out_path, cache_dir=out_path.parent / "cache"
)
pipeline = GenerationPipeline(pipeline_config, now_fn=lambda: datetime(2020, 1, 1, tzinfo=UTC))
pipeline.run(jobs, OfflineTemplateRenderer())
"""


def _generate_with_hash_seed(tmp_path: Path, name: str, hash_seed: str) -> bytes:
    script_path = tmp_path / f"{name}_gen.py"
    script_path.write_text(_GENERATE_SCRIPT, encoding="utf-8")
    out_path = tmp_path / f"{name}.jsonl"
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), str(out_path)],
        check=True,
        env=env,
        cwd=_REPO_ROOT,
    )
    return out_path.read_bytes()


@pytest.mark.slow
def test_generation_is_byte_identical_across_hash_seeds(tmp_path: Path) -> None:
    first = _generate_with_hash_seed(tmp_path, "run_a", "0")
    second = _generate_with_hash_seed(tmp_path, "run_b", "1")
    assert first == second
