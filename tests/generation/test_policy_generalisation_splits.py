"""Policy-generalisation splits must be non-empty and carry both label values.

Runs the exact fixture-scale config (``configs/data/fixtures.yaml``) through
generation and splitting, so a regression that starves ``heldout_policy_kind`` or
``heldout_policy_phrasing`` of positives or negatives fails here rather than only
showing up on the full ``train_medium`` run.
"""

from __future__ import annotations

from pathlib import Path

from forecheck.contracts import Example, RiskDimension, Split
from forecheck.data.splitting import assert_no_leakage, split_examples
from forecheck.generation.config import build_jobs, load_generation_config
from forecheck.generation.pipeline import GenerationPipeline, PipelineConfig
from forecheck.generation.renderers import OfflineTemplateRenderer

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "data" / "fixtures.yaml"


def _generate(tmp_path: Path) -> dict[Split, list[Example]]:
    config = load_generation_config(_CONFIG_PATH)
    jobs = build_jobs(config)
    pipeline_config = PipelineConfig(
        master_seed=config.seed,
        output_path=tmp_path / "raw.jsonl",
        cache_dir=tmp_path / ".cache",
    )
    pipeline = GenerationPipeline(pipeline_config)
    examples = pipeline.run(jobs, OfflineTemplateRenderer())
    splits = split_examples(examples)
    assert_no_leakage(splits)
    return splits


def test_heldout_policy_kind_and_phrasing_have_both_label_values_at_fixture_scale(
    tmp_path: Path,
) -> None:
    splits = _generate(tmp_path)
    for split in (Split.HELDOUT_POLICY_KIND, Split.HELDOUT_POLICY_PHRASING):
        rows = splits[split]
        assert len(rows) > 0
        values = {e.labels.values[RiskDimension.POLICY_CONFLICT] for e in rows}
        assert {v.value for v in values} & {"yes"}
        assert {v.value for v in values} & {"no"}


def test_heldout_policy_splits_are_disjoint_from_train_and_calibration(tmp_path: Path) -> None:
    splits = _generate(tmp_path)
    train_ids = {e.example_id for e in splits[Split.TRAIN]}
    calibration_ids = {e.example_id for e in splits[Split.CALIBRATION]}
    for split in (Split.HELDOUT_POLICY_KIND, Split.HELDOUT_POLICY_PHRASING):
        ids = {e.example_id for e in splits[split]}
        assert ids.isdisjoint(train_ids)
        assert ids.isdisjoint(calibration_ids)
