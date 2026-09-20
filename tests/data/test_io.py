from __future__ import annotations

import random
from datetime import UTC, datetime
from pathlib import Path

from forecheck.contracts import (
    Example,
    LabelSet,
    LabelValue,
    Provenance,
    RiskDimension,
    Split,
)
from forecheck.data.io import build_manifest, read_jsonl, sha256_file, verify_manifest, write_jsonl
from forecheck.data.rendering import OfflineTemplateRenderer
from forecheck.version import LABEL_DERIVATION_VERSION
from tests.data.factories import make_latent


def _make_example(scenario_id: str, *, positive: bool = False) -> Example:
    latent = make_latent(scenario_id=scenario_id, family_id=f"fam-{scenario_id}")
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    values = dict.fromkeys(RiskDimension, LabelValue.NO)
    if positive:
        values[RiskDimension.FINANCIAL_COMMITMENT] = LabelValue.YES
    labels = LabelSet(values=values, derivation_version=LABEL_DERIVATION_VERSION)
    provenance = Provenance(
        generator_name="test", generator_version="0.0.1", seed=0, created_at=datetime.now(tz=UTC)
    )
    return Example(
        example_id=f"ex-{scenario_id}",
        family_id=latent.family_id,
        latent=latent,
        context=context,
        labels=labels,
        provenance=provenance,
    )


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    examples = [_make_example("a"), _make_example("b", positive=True)]
    path = tmp_path / "shard.jsonl"
    write_jsonl(path, examples)
    read_back = read_jsonl(path)
    assert [e.example_id for e in read_back] == [e.example_id for e in examples]


def test_read_jsonl_on_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_jsonl(tmp_path / "missing.jsonl") == []


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "shard.jsonl"
    write_jsonl(path, [_make_example("a")])
    assert sha256_file(path) == sha256_file(path)


def test_build_manifest_computes_positive_rate(tmp_path: Path) -> None:
    examples = [_make_example("a"), _make_example("b", positive=True)]
    path = tmp_path / "shard.jsonl"
    write_jsonl(path, examples)
    manifest = build_manifest(Split.TRAIN, path, examples)
    assert manifest.n_examples == 2
    assert manifest.n_families == 2
    assert manifest.positive_rate[RiskDimension.FINANCIAL_COMMITMENT] == 0.5
    assert manifest.positive_rate[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] == 0.0


def test_verify_manifest_detects_tampering(tmp_path: Path) -> None:
    examples = [_make_example("a")]
    path = tmp_path / "shard.jsonl"
    write_jsonl(path, examples)
    manifest = build_manifest(Split.TRAIN, path, examples)
    assert verify_manifest(manifest, path) is True
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert verify_manifest(manifest, path) is False
