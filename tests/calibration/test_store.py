from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from forecheck.calibration.base import CalibratorBundle
from forecheck.calibration.store import load_bundle, save_bundle
from forecheck.contracts import LABEL_SCHEMA_VERSION


def _bundle(**overrides: object) -> CalibratorBundle:
    defaults: dict[str, object] = {
        "artifact_id": "artifact-1",
        "backend_model_id": "mock-heuristic-v1",
        "prompt_contract_hash": "abc123",
        "label_schema_version": LABEL_SCHEMA_VERSION,
        "split_name": "calibration",
        "dataset_sha256": "deadbeef",
        "fitted_at": datetime.now(UTC),
        "forecheck_version": "0.1.0",
        "dimensions": {},
    }
    defaults.update(overrides)
    return CalibratorBundle(**defaults)  # type: ignore[arg-type]


def test_save_creates_json_and_sha256_sidecar(tmp_path: Path) -> None:
    bundle = _bundle()
    path = tmp_path / "bundle.json"
    save_bundle(bundle, path)
    assert path.exists()
    assert (tmp_path / "bundle.json.sha256").exists()


def test_load_round_trips_bundle(tmp_path: Path) -> None:
    bundle = _bundle()
    path = tmp_path / "bundle.json"
    save_bundle(bundle, path)
    loaded = load_bundle(path)
    assert loaded.artifact_id == bundle.artifact_id
    assert loaded.prompt_contract_hash == bundle.prompt_contract_hash


def test_load_detects_checksum_corruption(tmp_path: Path) -> None:
    bundle = _bundle()
    path = tmp_path / "bundle.json"
    save_bundle(bundle, path)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="sha256"):
        load_bundle(path)


def test_load_rejects_mismatched_label_schema_version(tmp_path: Path) -> None:
    bundle = _bundle(label_schema_version="99.0")
    path = tmp_path / "bundle.json"
    save_bundle(bundle, path)
    with pytest.raises(ValueError, match="label_schema_version"):
        load_bundle(path)


def test_load_without_sidecar_still_works(tmp_path: Path) -> None:
    bundle = _bundle()
    path = tmp_path / "bundle.json"
    save_bundle(bundle, path)
    (tmp_path / "bundle.json.sha256").unlink()
    loaded = load_bundle(path)
    assert loaded.artifact_id == bundle.artifact_id
