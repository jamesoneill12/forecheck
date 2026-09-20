"""``forecheck model-card --run <dir>``: fill docs/model-card-template.md from a run."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from forecheck.calibration.store import load_bundle
from forecheck.cli_cmds._common import load_resolved_train_config
from forecheck.contracts import LABEL_SCHEMA_VERSION
from forecheck.data.io import sha256_file
from forecheck.evaluation.report import EvaluationReport
from forecheck.version import LABEL_DERIVATION_VERSION, __version__

__all__ = ["model_card_command"]

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
_NOT_MEASURED = "not measured"


def _locate_template() -> Path:
    relative = Path("docs") / "model-card-template.md"
    here = Path(__file__).resolve()
    for base in (Path.cwd(), *here.parents):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"could not locate {relative} from {Path.cwd()} or {here}")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _manifest_values(data_dir: Path, split: str, prefix: str) -> dict[str, str]:
    manifest_path = data_dir / f"{split}.manifest.json"
    manifest = _read_json(manifest_path)
    if manifest is None:
        return {}
    return {
        f"n_{prefix}": str(manifest["n_examples"]),
        f"n_{prefix}_families": str(manifest["n_families"]),
        f"{prefix}_sha256": manifest["sha256"],
    }


def _fmt(value: float | None) -> str:
    return _NOT_MEASURED if value is None else f"{value:.4f}"


def _training_values(run: Path) -> dict[str, str]:
    train_config = load_resolved_train_config(run)
    if train_config is None:
        return {}
    config_path = run / "config.resolved.yaml"
    values = {
        "base_model_id": train_config.model.base_id,
        "base_revision": train_config.model.revision or "n/a",
        "lora_r": str(train_config.lora.r),
        "lora_alpha": str(train_config.lora.alpha),
        "lora_targets": ", ".join(train_config.lora.target_modules),
        "seed": str(train_config.train.seed),
        "micro_batch": str(train_config.optim.micro_batch_size),
        "grad_accum": str(train_config.optim.grad_accum),
        "effective_batch": str(train_config.optim.micro_batch_size * train_config.optim.grad_accum),
        "optimizer": "AdamW",
        "lr": str(train_config.optim.lr),
        "schedule": train_config.optim.scheduler,
        "epochs": str(train_config.optim.epochs),
        "precision": train_config.model.dtype,
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "tracking_uri": train_config.tracking.uri or train_config.tracking.backend,
        "data_config": str(config_path),
        "train_config": str(config_path),
        "run_dir": str(run),
        "data_dir": str(train_config.data.dir),
    }
    values.update(_manifest_values(train_config.data.dir, "train", "train"))
    values.update(_manifest_values(train_config.data.dir, "calibration", "cal"))
    values.update(_manifest_values(train_config.data.dir, "test", "test"))
    return values


def _env_values(run: Path) -> dict[str, str]:
    env = _read_json(run / "env.json")
    if env is None:
        return {}
    return {
        "git_sha": str(env.get("git", {}).get("sha") or _NOT_MEASURED),
        "hardware": str(env.get("device", {}).get("device", _NOT_MEASURED)),
    }


def _prompt_contract_values(run: Path) -> dict[str, str]:
    prompt_contract = _read_json(run / "prompt_contract.json")
    if prompt_contract is None:
        return {}
    return {"prompt_contract_hash": str(prompt_contract.get("hash", _NOT_MEASURED))}


def _calibration_values(run: Path) -> dict[str, str]:
    bundle_path = run / "calibration" / "bundle.json"
    if not bundle_path.exists():
        return {}
    bundle = load_bundle(bundle_path)
    degenerate = sorted(d.dimension.value for d in bundle.dimensions.values() if d.degenerate)
    methods = sorted({d.method.value for d in bundle.dimensions.values()})
    eces_before = [d.ece_before for d in bundle.dimensions.values() if d.ece_before is not None]
    eces_after = [d.ece_after for d in bundle.dimensions.values() if d.ece_after is not None]
    values = {
        "calibration_artifact_id": bundle.artifact_id,
        "calibration_sha256": sha256_file(bundle_path),
        "calibration_method": ", ".join(methods) if methods else "none",
        "degenerate_dims_or_none": ", ".join(degenerate) if degenerate else "none",
    }
    if eces_before:
        values["ece_before"] = f"{sum(eces_before) / len(eces_before):.4f}"
    if eces_after:
        values["ece_after"] = f"{sum(eces_after) / len(eces_after):.4f}"
    return values


def _evaluation_values(run: Path) -> dict[str, str]:
    report_path = run / "reports" / "test" / "report.json"
    if not report_path.exists():
        return {}
    report = EvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    values = {
        "macro_auprc": _fmt(report.macro.get("auprc")),
        "macro_f1": _fmt(report.macro.get("f1")),
        "macro_brier": _fmt(report.macro.get("brier")),
        "macro_ece": _fmt(report.macro.get("ece")),
        "eval_seed": str(report.seed),
    }
    values["auprc"] = values["macro_auprc"]
    values["ece"] = values["macro_ece"]
    if report.dataset.n:
        values["n_test"] = str(report.dataset.n)
    if report.dataset.sha256:
        values["test_sha256"] = report.dataset.sha256
    return values


def _build_values(run: Path) -> dict[str, str]:
    values: dict[str, str] = {
        "forecheck_version": __version__,
        "label_schema_version": LABEL_SCHEMA_VERSION,
        "label_derivation_version": LABEL_DERIVATION_VERSION,
        "date": datetime.now(UTC).date().isoformat(),
    }
    values.update(_training_values(run))
    values.update(_env_values(run))
    values.update(_prompt_contract_values(run))
    values.update(_calibration_values(run))
    values.update(_evaluation_values(run))
    return values


def model_card_command(
    run: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    out: Annotated[Path | None, typer.Option(help="Output path.")] = None,
) -> None:
    """Fill docs/model-card-template.md placeholders from a run's captured artifacts."""
    template = _locate_template().read_text(encoding="utf-8")
    values = _build_values(run)
    filled = _PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), _NOT_MEASURED), template)
    out_path = out or (run / "model-card.md")
    out_path.write_text(filled, encoding="utf-8")
    typer.echo(f"wrote {out_path}")
