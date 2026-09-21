from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer

from forecheck.calibration.base import CalibratorBundle
from forecheck.calibration.store import save_bundle
from forecheck.cli_cmds._common import resolve_backend
from forecheck.cli_cmds.evaluate import evaluate_command
from forecheck.contracts import LABEL_SCHEMA_VERSION
from forecheck.data.io import write_jsonl
from forecheck.evaluation.report import EvaluationClass
from forecheck.version import __version__
from tests.evaluation.conftest import make_example


def _write_split(data_dir: Path, name: str, n: int = 3) -> None:
    examples = [
        make_example(example_id=f"{name}-{i}", family_id=f"{name}-fam-{i}") for i in range(n)
    ]
    write_jsonl(data_dir / f"{name}.jsonl", examples)


def _write_guardian_config(path: Path) -> None:
    path.write_text(
        "model_id: toy/model\nfamily: granite_guardian\n",
        encoding="utf-8",
    )


def test_resolve_backend_guardian_requires_config(tmp_path: Path) -> None:
    with pytest.raises(typer.BadParameter, match="--backend-config"):
        resolve_backend("guardian", tmp_path / "run")


def test_resolve_backend_guardian_builds_backend_from_config(tmp_path: Path) -> None:
    from forecheck.inference.guardian import GuardianBackend

    config_path = tmp_path / "guardian.yaml"
    _write_guardian_config(config_path)

    backend = resolve_backend("guardian", tmp_path / "run", config=config_path)

    assert isinstance(backend, GuardianBackend)
    assert backend._config.model_id == "toy/model"
    assert backend._config.strip_identity is False


def test_resolve_backend_guardian_applies_strip_identity(tmp_path: Path) -> None:
    config_path = tmp_path / "guardian.yaml"
    _write_guardian_config(config_path)

    backend = resolve_backend("guardian", tmp_path / "run", config=config_path, strip_identity=True)

    assert backend._config.strip_identity is True


def test_evaluate_command_records_identity_stripped_false_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=False,
        data=data_dir,
    )

    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["identity_stripped"] is False
    markdown = (run_dir / "reports" / "test" / "report.md").read_text()
    assert "Identity stripped: false" in markdown


def test_evaluate_command_strip_identity_flag_records_true_and_skips_calibration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    calibration_dir = run_dir / "calibration"
    calibration_dir.mkdir(parents=True)
    bundle = CalibratorBundle(
        artifact_id="bundle-1",
        backend_model_id="mock-heuristic-v1",
        prompt_contract_hash="n/a",
        label_schema_version=LABEL_SCHEMA_VERSION,
        split_name="calibration",
        dataset_sha256="deadbeef",
        fitted_at=datetime.now(UTC),
        forecheck_version=__version__,
        dimensions={},
    )
    save_bundle(bundle, calibration_dir / "bundle.json")

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=True,
        data=data_dir,
    )

    captured = capsys.readouterr()
    assert "skipping calibration bundle: --strip-identity was set" in captured.out

    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["identity_stripped"] is True
    assert report["calibration"]["method"] == "none"
    markdown = (run_dir / "reports" / "test" / "report.md").read_text()
    assert "Identity stripped: true" in markdown


def test_evaluate_command_guardian_backend_creates_missing_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forecheck.inference.guardian import GuardianBackend

    class _Sentinel(Exception):
        pass

    def _raise_instead_of_loading(self: GuardianBackend) -> None:
        raise _Sentinel("no network in tests")

    monkeypatch.setattr(GuardianBackend, "_ensure_loaded", _raise_instead_of_loading)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "fresh-run"
    assert not run_dir.exists()
    config_path = tmp_path / "guardian.yaml"
    _write_guardian_config(config_path)

    with pytest.raises(_Sentinel):
        evaluate_command(
            run=run_dir,
            split="test",
            evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
            backend="guardian",
            backend_config=config_path,
            strip_identity=False,
            data=data_dir,
        )

    assert run_dir.exists()


def test_evaluate_command_missing_run_dir_raises_for_non_guardian_backend(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "missing-run"

    with pytest.raises(typer.BadParameter, match="does not exist"):
        evaluate_command(
            run=run_dir,
            split="test",
            evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
            backend="mock",
            backend_config=None,
            strip_identity=False,
            data=data_dir,
        )


def test_evaluate_command_max_examples_subsamples_split(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test", n=12)
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=False,
        data=data_dir,
        max_examples=5,
    )

    assert "seeded subsample of 5 rows" in capsys.readouterr().out
    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["dataset"]["n"] == 5


def test_evaluate_command_stacking_synthetic_writes_stacking_section(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=False,
        data=data_dir,
        stacking_bundles=None,
        stacking_synthetic=True,
    )

    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["stacking"] is not None
    assert len(report["stacking"]["rows"]) == 33
    markdown = (run_dir / "reports" / "test" / "report.md").read_text()
    assert "## Multi-policy stacking" in markdown


def test_evaluate_command_stacking_bundles_and_synthetic_combine(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=False,
        data=data_dir,
        stacking_bundles="balanced,conservative",
        stacking_synthetic=True,
    )

    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["stacking"] is not None
    max_k = max(row["k"] for row in report["stacking"]["rows"])
    assert max_k == 13


def test_evaluate_command_without_stacking_flags_omits_stacking(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    evaluate_command(
        run=run_dir,
        split="test",
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        backend="mock",
        backend_config=None,
        strip_identity=False,
        data=data_dir,
    )

    report = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    assert report["stacking"] is None


def test_resolve_data_dir_reads_encoder_run_config(tmp_path: Path) -> None:
    from forecheck.cli_cmds._common import resolve_data_dir

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.resolved.yaml").write_text(
        "model:\n  base_id: toy\n  pooling: mean\n  max_tokens: 64\n"
        "data:\n  dir: /data/v2\noptim:\n  backbone_lr: 1.0e-5\n",
        encoding="utf-8",
    )

    assert resolve_data_dir(None, run_dir) == Path("/data/v2")


def test_evaluate_command_caches_threshold_selection_scores(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "dev")
    _write_split(data_dir, "test")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    kwargs: dict[str, object] = {
        "run": run_dir,
        "split": "test",
        "evaluation_class": EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        "backend": "mock",
        "backend_config": None,
        "strip_identity": False,
        "data": data_dir,
    }

    evaluate_command(**kwargs)
    first = json.loads((run_dir / "reports" / "test" / "report.json").read_text())
    cache_files = list((run_dir / "cache").glob("raw-scores-dev-*.json"))
    assert len(cache_files) == 1

    evaluate_command(**kwargs)
    out = capsys.readouterr().out
    second = json.loads((run_dir / "reports" / "test" / "report.json").read_text())

    assert "reusing cached dev scores" in out
    assert first["dimensions"] == second["dimensions"]
