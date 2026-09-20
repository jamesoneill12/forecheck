"""Training configuration: pydantic schema, YAML loading and dotted overrides.

``TrainConfig`` is the single source of truth for a run. It is loaded from a YAML file
and then patched with ``key.sub=value`` command-line overrides (the form the EKS
recipes use, e.g. ``data.dir=/opt/ml/fsx/... output.dir=/opt/ml/fsx/...``), validated,
and dumped verbatim into the run directory by :mod:`forecheck.training.capture`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecheck.contracts import Limits, RiskDimension, Split

__all__ = [
    "DataConfig",
    "LoraConfig",
    "ModelConfig",
    "OptimConfig",
    "OutputConfig",
    "TrackingConfig",
    "TrainConfig",
    "TrainLoopConfig",
    "apply_dotted_overrides",
    "load_config",
]

DType = Literal["auto", "bf16", "fp16", "fp32"]
Scheduler = Literal["linear", "cosine", "constant"]
TrackingBackend = Literal["local", "mlflow"]

_DATA_SPLITS: frozenset[Split] = frozenset({Split.TRAIN, Split.DEV})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelConfig(_Strict):
    base_id: str
    revision: str | None = None
    dtype: DType = "auto"
    attn_implementation: str | None = None


class LoraConfig(_Strict):
    r: int = Field(default=16, gt=0)
    alpha: int = Field(default=32, gt=0)
    dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    target_modules: tuple[str, ...] = ("q_proj", "k_proj", "v_proj", "o_proj")
    qlora: bool = False


class DataConfig(_Strict):
    dir: Path
    train_split: Split = Split.TRAIN
    dev_split: Split = Split.DEV
    max_prompt_tokens: int = Field(default=Limits.MAX_PROMPT_TOKENS, gt=0)
    dimension_weights: dict[RiskDimension, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_splits(self) -> DataConfig:
        for name, split in (("train_split", self.train_split), ("dev_split", self.dev_split)):
            if split not in _DATA_SPLITS:
                raise ValueError(
                    f"data.{name}={split.value!r} is not usable for training; "
                    f"only {sorted(s.value for s in _DATA_SPLITS)} are allowed"
                )
        return self


class OptimConfig(_Strict):
    lr: float = Field(default=2e-4, gt=0.0)
    weight_decay: float = Field(default=0.0, ge=0.0)
    warmup_ratio: float = Field(default=0.03, ge=0.0, lt=1.0)
    epochs: int = Field(default=1, gt=0)
    max_steps: int | None = Field(default=None, gt=0)
    micro_batch_size: int = Field(default=1, gt=0)
    grad_accum: int = Field(default=1, gt=0)
    grad_clip: float = Field(default=1.0, gt=0.0)
    scheduler: Scheduler = "cosine"


class TrainLoopConfig(_Strict):
    seed: int = 0
    eval_every: int = Field(default=50, gt=0)
    save_every: int = Field(default=50, gt=0)
    early_stop_patience: int = Field(default=3, gt=0)
    resume_from: Path | None = None
    shared_prefill: bool = True


class TrackingConfig(_Strict):
    backend: TrackingBackend = "local"
    uri: str | None = None
    run_name: str | None = None


class OutputConfig(_Strict):
    dir: Path


class TrainConfig(_Strict):
    model: ModelConfig
    lora: LoraConfig = Field(default_factory=LoraConfig)
    data: DataConfig
    optim: OptimConfig = Field(default_factory=OptimConfig)
    train: TrainLoopConfig = Field(default_factory=TrainLoopConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    output: OutputConfig

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=True)


def _set_dotted(data: dict[str, object], dotted_key: str, value: object) -> None:
    parts = dotted_key.split(".")
    cursor = data
    for part in parts[:-1]:
        existing = cursor.get(part)
        if not isinstance(existing, dict):
            existing = {}
            cursor[part] = existing
        cursor = existing
    cursor[parts[-1]] = value


def apply_dotted_overrides(data: dict[str, object], overrides: list[str]) -> dict[str, object]:
    """Apply ``key.sub=value`` overrides onto a raw config mapping, in order.

    Values are parsed with ``yaml.safe_load`` so ``true``/``42``/``1.5`` become their
    native types while anything else stays a string.
    """
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"override {override!r} is not of the form key.sub=value")
        key, raw_value = override.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"override {override!r} has an empty key")
        value = yaml.safe_load(raw_value)
        _set_dotted(data, key, value)
    return data


def load_config(path: Path, overrides: list[str] | None = None) -> TrainConfig:
    """Load a :class:`TrainConfig` from YAML, apply dotted overrides, and validate."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"config file {path} did not parse to a mapping")
    data: dict[str, object] = raw
    if overrides:
        data = apply_dotted_overrides(data, overrides)
    return TrainConfig.model_validate(data)
