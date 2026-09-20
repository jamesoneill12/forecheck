from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from forecheck.training.tracking import LocalJsonTracker, MlflowTracker

HAS_MLFLOW = importlib.util.find_spec("mlflow") is not None


def test_local_tracker_writes_params_and_metrics(tmp_path: Path) -> None:
    tracker = LocalJsonTracker(tmp_path)

    tracker.log_params({"lr": 0.001, "model": "tiny"})
    tracker.log_metrics(1, {"train/loss": 1.5})
    tracker.log_metrics(2, {"train/loss": 1.2})
    tracker.finish()

    params = json.loads((tmp_path / "params.json").read_text(encoding="utf-8"))
    assert params == {"lr": 0.001, "model": "tiny"}
    lines = (tmp_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert records == [{"step": 1, "train/loss": 1.5}, {"step": 2, "train/loss": 1.2}]


def test_local_tracker_records_artifacts(tmp_path: Path) -> None:
    tracker = LocalJsonTracker(tmp_path)
    artifact = tmp_path / "adapter.safetensors"
    artifact.write_text("fake", encoding="utf-8")

    tracker.log_artifact(artifact)

    manifest = json.loads((tmp_path / "artifacts.json").read_text(encoding="utf-8"))
    assert manifest == [str(artifact)]


@pytest.mark.skipif(HAS_MLFLOW, reason="only exercises the missing-mlflow error path")
def test_mlflow_tracker_raises_a_clear_error_when_mlflow_is_missing() -> None:
    with pytest.raises(ImportError, match="mlflow"):
        MlflowTracker("file:///tmp/mlruns")
