"""Shared helpers for the ``calibrate``/``evaluate``/``model-card`` CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer
import yaml

from forecheck.calibration.methods import calibrator_for_method
from forecheck.contracts import ErrorCode, ForecheckError, RiskDimension
from forecheck.inference import (
    AgentSelfBackend,
    EncoderBackend,
    EncoderBackendConfig,
    GuardianBackend,
    HFBackend,
    HFBackendConfig,
    MockBackend,
    load_agent_self_config,
    load_guardian_config,
)
from forecheck.inference.encoder import HEAD_CONFIG_FILE, head_checkpoint_dir
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
    """Load ``<run>/config.resolved.yaml`` as a decoder :class:`TrainConfig`, if present.

    Returns ``None`` both when the file is absent and when it does not parse as a
    decoder ``TrainConfig`` (e.g. an encoder run's config), since callers use this to
    opportunistically inspect a decoder run rather than to assert its shape.
    """
    path = run / "config.resolved.yaml"
    if not path.exists():
        return None
    from pydantic import ValidationError

    from forecheck.training.config import TrainConfig

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        return TrainConfig.model_validate(raw)
    except ValidationError:
        return None


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


def resolve_backend(
    name: str,
    run: Path,
    *,
    config: Path | None = None,
    strip_identity: bool = False,
) -> ClassifierBackend:
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
        hf_config = HFBackendConfig(
            model_id=train_config.model.base_id,
            revision=train_config.model.revision,
            adapter_id=str(adapter_dir) if adapter_dir is not None else None,
            strip_identity=strip_identity or train_config.data.strip_identity,
        )
        return HFBackend(hf_config)
    if name == "encoder":
        head_config_path = head_checkpoint_dir(run) / HEAD_CONFIG_FILE
        if not head_config_path.exists():
            raise typer.BadParameter(
                f"--backend encoder requires {head_config_path} (an encoder-trained run); "
                "pass --backend mock or --backend rule_baseline otherwise"
            )
        head_config = json.loads(head_config_path.read_text(encoding="utf-8"))
        encoder_config = EncoderBackendConfig(
            model_id=head_config["model_id"],
            run_dir=run,
            pooling=head_config["pooling"],
            max_tokens=head_config["max_tokens"],
            strip_identity=strip_identity,
        )
        return EncoderBackend(encoder_config)
    if name == "guardian":
        if config is None:
            raise typer.BadParameter("--backend guardian requires --backend-config PATH")
        guardian_config = load_guardian_config(config)
        if strip_identity:
            from dataclasses import replace

            guardian_config = replace(guardian_config, strip_identity=True)
        return GuardianBackend(guardian_config)
    if name == "agent_self":
        agent_self_config = load_agent_self_config(config) if config is not None else None
        if agent_self_config is None:
            from forecheck.inference.agent_self import AgentSelfBackendConfig

            agent_self_config = AgentSelfBackendConfig()
        if strip_identity:
            from dataclasses import replace

            agent_self_config = replace(agent_self_config, strip_identity=True)
        return AgentSelfBackend(agent_self_config)
    raise typer.BadParameter(
        f"unknown backend {name!r}, expected mock|hf|rule_baseline|encoder|guardian|agent_self"
    )


def resolve_data_dir(data: Path | None, run: Path) -> Path:
    if data is not None:
        return data
    path = run / "config.resolved.yaml"
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data_dir = (raw.get("data") or {}).get("dir")
        if data_dir:
            return Path(data_dir)
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
