from __future__ import annotations

import json
from pathlib import Path

import yaml

from forecheck.contracts import Split
from forecheck.data.io import sha256_file, write_jsonl
from forecheck.inference.prompt import PROMPT_CONTRACT_HASH, QUESTIONS
from forecheck.training.capture import (
    capture_env,
    capture_prompt_contract,
    compute_data_hashes,
    git_info,
    write_checkpoint_manifest,
    write_run_capture,
)
from forecheck.training.config import DataConfig, ModelConfig, OutputConfig, TrainConfig
from tests.training.conftest import make_training_example


def test_capture_prompt_contract_matches_the_live_hash() -> None:
    captured = capture_prompt_contract()

    assert captured["hash"] == PROMPT_CONTRACT_HASH
    assert set(captured["questions"]) == {d.value for d in QUESTIONS}
    assert captured["strip_identity"] is False


def test_capture_prompt_contract_records_strip_identity() -> None:
    captured = capture_prompt_contract(strip_identity=True)

    assert captured["strip_identity"] is True


def test_git_info_returns_a_well_typed_result() -> None:
    info = git_info(Path(__file__).resolve().parents[2])

    assert info["sha"] is None or (isinstance(info["sha"], str) and len(info["sha"]) == 40)
    assert info["dirty"] is None or isinstance(info["dirty"], bool)


def test_git_info_is_safe_outside_a_repo(tmp_path: Path) -> None:
    info = git_info(tmp_path)

    assert info["sha"] is None
    assert info["dirty"] is None


def test_capture_env_reports_optional_packages_and_device() -> None:
    env = capture_env()

    assert "torch" in env["packages"]
    device = env["device"]
    assert device["device"] in {"cpu", "mps", "cuda"}
    assert device["device"] == "cuda" or device["cuda_available"] is False
    assert (
        device["device"] == "mps" or device["mps_available"] is False or device["device"] == "cuda"
    )


def test_compute_data_hashes_matches_sha256_file(tmp_path: Path) -> None:
    example = make_training_example("ex-1")
    write_jsonl(tmp_path / "train.jsonl", [example])
    write_jsonl(tmp_path / "dev.jsonl", [example])

    hashes = compute_data_hashes(tmp_path, [Split.TRAIN, Split.DEV])

    assert hashes["train"] == sha256_file(tmp_path / "train.jsonl")
    assert hashes["dev"] == sha256_file(tmp_path / "dev.jsonl")


def test_write_run_capture_writes_all_expected_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    example = make_training_example("ex-1")
    write_jsonl(data_dir / "train.jsonl", [example])
    write_jsonl(data_dir / "dev.jsonl", [example])
    run_dir = tmp_path / "run"
    config = TrainConfig(
        model=ModelConfig(base_id="test/tiny"),
        data=DataConfig(dir=data_dir),
        output=OutputConfig(dir=run_dir),
    )

    write_run_capture(run_dir, config)

    resolved = yaml.safe_load((run_dir / "config.resolved.yaml").read_text(encoding="utf-8"))
    assert resolved["model"]["base_id"] == "test/tiny"
    data_hashes = json.loads((run_dir / "data_hashes.json").read_text(encoding="utf-8"))
    assert set(data_hashes) == {"train", "dev"}
    prompt_contract = json.loads((run_dir / "prompt_contract.json").read_text(encoding="utf-8"))
    assert prompt_contract["hash"] == PROMPT_CONTRACT_HASH
    assert prompt_contract["strip_identity"] is False
    env = json.loads((run_dir / "env.json").read_text(encoding="utf-8"))
    assert "python_version" in env


def test_write_run_capture_records_strip_identity_true(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    example = make_training_example("ex-1")
    write_jsonl(data_dir / "train.jsonl", [example])
    write_jsonl(data_dir / "dev.jsonl", [example])
    run_dir = tmp_path / "run"
    config = TrainConfig(
        model=ModelConfig(base_id="test/tiny"),
        data=DataConfig(dir=data_dir, strip_identity=True),
        output=OutputConfig(dir=run_dir),
    )

    write_run_capture(run_dir, config)

    resolved = yaml.safe_load((run_dir / "config.resolved.yaml").read_text(encoding="utf-8"))
    assert resolved["data"]["strip_identity"] is True
    prompt_contract = json.loads((run_dir / "prompt_contract.json").read_text(encoding="utf-8"))
    assert prompt_contract["strip_identity"] is True


def test_write_checkpoint_manifest(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints" / "step-10"

    path = write_checkpoint_manifest(
        checkpoint_dir, step=10, files={"optimizer.pt": "abc123"}, extra={"epoch": 1}
    )

    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["step"] == 10
    assert manifest["files"] == {"optimizer.pt": "abc123"}
    assert manifest["epoch"] == 1
