"""Shared helpers for the ``calibrate``/``evaluate``/``model-card`` CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
import yaml

from forecheck.calibration.methods import calibrator_for_method
from forecheck.contracts import ErrorCode, ForecheckError, RiskDimension
from forecheck.inference import HFBackend, HFBackendConfig, MockBackend
from forecheck.policies.builtin import available_bundle_names, load_builtin_engine
from forecheck.policies.loader import load_policy_engine

if TYPE_CHECKING:
    from forecheck.calibration.base import Calibrator, CalibratorBundle
    from forecheck.inference.base import ClassifierBackend
    from forecheck.policies.engine import DeterministicPolicyEngine
    from forecheck.training.config import TrainConfig

__all__ = [
    "calibrators_from_bundle",
    "load_policy_engine_by_name_or_path",
    "load_resolved_train_config",
    "resolve_backend",
    "resolve_data_dir",
]


def load_resolved_train_config(run: Path) -> TrainConfig | None:
    path = run / "config.resolved.yaml"
    if not path.exists():
        return None
    from forecheck.training.config import TrainConfig

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TrainConfig.model_validate(raw)


def _latest_checkpoint_adapter(run: Path) -> Path | None:
    checkpoints_dir = run / "checkpoints"
    if not checkpoints_dir.is_dir():
        return None
    steps: list[tuple[int, Path]] = []
    for candidate in checkpoints_dir.glob("step-*"):
        adapter = candidate / "adapter"
        if adapter.is_dir():
            try:
                step = int(candidate.name.removeprefix("step-"))
            except ValueError:
                continue
            steps.append((step, adapter))
    if not steps:
        return None
    return max(steps, key=lambda item: item[0])[1]


def resolve_backend(name: str, run: Path) -> ClassifierBackend:
    if name == "mock":
        return MockBackend()
    if name == "rule_baseline":
        from forecheck.evaluation.baselines import RuleBaselineBackend

        return RuleBaselineBackend()
    if name == "hf":
        train_config = load_resolved_train_config(run)
        if train_config is None:
            raise typer.BadParameter(
                f"--backend hf requires {run / 'config.resolved.yaml'} (a trained run); "
                "pass --backend mock or --backend rule_baseline otherwise"
            )
        adapter_dir = _latest_checkpoint_adapter(run)
        config = HFBackendConfig(
            model_id=train_config.model.base_id,
            revision=train_config.model.revision,
            adapter_id=str(adapter_dir) if adapter_dir is not None else None,
        )
        return HFBackend(config)
    raise typer.BadParameter(f"unknown backend {name!r}, expected mock|hf|rule_baseline")


def resolve_data_dir(data: Path | None, run: Path) -> Path:
    if data is not None:
        return data
    train_config = load_resolved_train_config(run)
    if train_config is not None:
        return train_config.data.dir
    raise typer.BadParameter("pass --data <dir>: no config.resolved.yaml found under --run")


def calibrators_from_bundle(bundle: CalibratorBundle) -> dict[RiskDimension, Calibrator]:
    calibrators: dict[RiskDimension, Calibrator] = {}
    for dimension, dim_cal in bundle.dimensions.items():
        if dim_cal.degenerate:
            continue
        calibrators[dimension] = calibrator_for_method(dim_cal.method).from_params(dim_cal.params)
    return calibrators


def load_policy_engine_by_name_or_path(bundle: str) -> DeterministicPolicyEngine:
    if bundle in available_bundle_names():
        return load_builtin_engine(bundle)
    path = Path(bundle)
    if not path.exists():
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_NOT_FOUND,
            f"policy bundle {bundle!r} is neither a built-in name "
            f"({', '.join(available_bundle_names())}) nor an existing file path",
        )
    return load_policy_engine(path)
