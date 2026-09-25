from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from forecheck.contracts import RiskDimension, Split
from forecheck.training.config import TrainConfig, apply_dotted_overrides, load_config

MINIMAL_YAML = """
model:
  base_id: test/tiny-model
data:
  dir: /tmp/does-not-need-to-exist
output:
  dir: /tmp/does-not-need-to-exist/run
"""


def test_load_minimal_config_applies_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path)

    assert config.model.base_id == "test/tiny-model"
    assert config.model.dtype == "auto"
    assert config.lora.r == 16
    assert config.data.train_split is Split.TRAIN
    assert config.data.dev_split is Split.DEV
    assert config.optim.scheduler == "cosine"
    assert config.train.shared_prefill is True
    assert config.tracking.backend == "local"
    assert config.data.strip_identity is False


def test_data_strip_identity_overridable_by_dotted_override(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path, overrides=["data.strip_identity=true"])

    assert config.data.strip_identity is True


def test_dotted_overrides_set_nested_fields_with_type_coercion(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(
        path,
        overrides=[
            "data.dir=/opt/ml/fsx/forecheck/data",
            "output.dir=/opt/ml/fsx/forecheck/runs/r1",
            "optim.lr=0.001",
            "optim.epochs=3",
            "lora.qlora=true",
            "train.shared_prefill=false",
        ],
    )

    assert str(config.data.dir) == "/opt/ml/fsx/forecheck/data"
    assert str(config.output.dir) == "/opt/ml/fsx/forecheck/runs/r1"
    assert config.optim.lr == pytest.approx(0.001)
    assert config.optim.epochs == 3
    assert config.lora.qlora is True
    assert config.train.shared_prefill is False


def test_apply_dotted_overrides_rejects_malformed_override() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        apply_dotted_overrides({}, ["not-an-override"])


def test_train_split_must_be_train_or_dev(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(MINIMAL_YAML)
    raw["data"]["train_split"] = "calibration"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError, match="not usable for training"):
        load_config(path)


def test_dev_split_must_be_train_or_dev(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(MINIMAL_YAML)
    raw["data"]["dev_split"] = "test"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError, match="not usable for training"):
        load_config(path)


def test_extra_fields_are_forbidden(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(MINIMAL_YAML)
    raw["not_a_real_field"] = 1
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


def test_dimension_weights_key_by_risk_dimension(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(MINIMAL_YAML)
    raw["data"]["dimension_weights"] = {"financial_commitment": 2.0}
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    config = load_config(path)

    assert config.data.dimension_weights == {RiskDimension.FINANCIAL_COMMITMENT: 2.0}


def test_lora_enabled_defaults_to_true(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path)

    assert config.lora.enabled is True


def test_lora_disabled_with_qlora_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    with pytest.raises(ValidationError, match="incompatible"):
        load_config(path, overrides=["lora.enabled=false", "lora.qlora=true"])


def test_train_gradient_checkpointing_defaults_to_false(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path)

    assert config.train.gradient_checkpointing is False


def test_train_keep_checkpoints_defaults_to_none(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path)

    assert config.train.keep_checkpoints is None


def test_train_keep_checkpoints_overridable_by_dotted_override(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path, overrides=["train.keep_checkpoints=2"])

    assert config.train.keep_checkpoints == 2


def test_data_dev_max_examples_defaults_to_none(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path)

    assert config.data.dev_max_examples is None


def test_data_dev_max_examples_overridable_by_dotted_override(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_config(path, overrides=["data.dev_max_examples=500"])

    assert config.data.dev_max_examples == 500


def test_resolved_config_round_trips_through_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")
    config = load_config(path)

    reloaded = TrainConfig.model_validate(yaml.safe_load(config.to_yaml()))

    assert reloaded == config
