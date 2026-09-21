from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from forecheck.training.config import (
    EncoderTrainConfig,
    apply_dotted_overrides,
    load_encoder_config,
)

MINIMAL_YAML = """
model:
  base_id: test/tiny-encoder
data:
  dir: /tmp/does-not-need-to-exist
output:
  dir: /tmp/does-not-need-to-exist/run
"""


def test_load_minimal_encoder_config_applies_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_encoder_config(path)

    assert config.model.base_id == "test/tiny-encoder"
    assert config.model.pooling == "mean"
    assert config.model.max_tokens == 2048
    assert config.optim.backbone_lr == pytest.approx(2e-5)
    assert config.optim.head_lr == pytest.approx(1e-3)
    assert config.optim.epochs == 3
    assert config.optim.micro_batch_size == 32
    assert config.train.freeze_backbone is False
    assert config.loss.pos_weight_mode == "none"
    assert config.tracking.backend == "local"


def test_encoder_dotted_overrides_set_nested_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")

    config = load_encoder_config(
        path,
        overrides=[
            "model.pooling=cls",
            "optim.micro_batch_size=8",
            "train.freeze_backbone=true",
            "loss.pos_weight_mode=balanced",
        ],
    )

    assert config.model.pooling == "cls"
    assert config.optim.micro_batch_size == 8
    assert config.train.freeze_backbone is True
    assert config.loss.pos_weight_mode == "balanced"


def test_encoder_extra_fields_are_forbidden(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(MINIMAL_YAML)
    raw["not_a_real_field"] = 1
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_encoder_config(path)


def test_encoder_config_round_trips_through_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_YAML, encoding="utf-8")
    config = load_encoder_config(path)

    reloaded = EncoderTrainConfig.model_validate(yaml.safe_load(config.to_yaml()))

    assert reloaded == config


def test_apply_dotted_overrides_still_rejects_malformed_override() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        apply_dotted_overrides({}, ["not-an-override"])
