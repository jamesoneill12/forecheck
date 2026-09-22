"""Everything a model card is regenerated from later: config, data, code and env.

Writes into a run directory: the resolved config, sha256 of every data file the run
consumed, the prompt contract (template/questions/hash) the run trained against, and
the environment (interpreter, optional package versions, git state, host, device). A
matching ``checkpoint_manifest.json`` is written beside every saved checkpoint.
"""

from __future__ import annotations

import json
import platform
import socket
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forecheck.contracts import Split
from forecheck.data.io import sha256_file
from forecheck.inference.prompt import (
    PROMPT_CONTRACT_HASH,
    QUESTIONS,
    SECTION_ORDER,
    SERIALIZATION_CONTRACT_HASH,
    SYSTEM_PREAMBLE,
)
from forecheck.version import PROMPT_CONTRACT_VERSION, __version__

if TYPE_CHECKING:
    from collections.abc import Iterable

    from forecheck.training.config import EncoderTrainConfig, TrainConfig

__all__ = [
    "capture_env",
    "capture_prompt_contract",
    "compute_data_hashes",
    "git_info",
    "write_checkpoint_manifest",
    "write_run_capture",
]

_OPTIONAL_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "peft",
    "accelerate",
    "bitsandbytes",
)


def capture_prompt_contract(*, strip_identity: bool = False) -> dict[str, Any]:
    return {
        "version": PROMPT_CONTRACT_VERSION,
        "hash": PROMPT_CONTRACT_HASH,
        "serialization_contract_hash": SERIALIZATION_CONTRACT_HASH,
        "system_preamble": SYSTEM_PREAMBLE,
        "section_order": list(SECTION_ORDER),
        "questions": {dimension.value: text for dimension, text in QUESTIONS.items()},
        "strip_identity": strip_identity,
    }


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _device_info() -> dict[str, Any]:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return {"cuda_available": False, "mps_available": False, "device": "cpu"}
    cuda_available = bool(torch.cuda.is_available())
    mps_backend = getattr(torch.backends, "mps", None)
    mps_available = bool(mps_backend is not None and mps_backend.is_available())
    device = "cuda" if cuda_available else "mps" if mps_available else "cpu"
    return {"cuda_available": cuda_available, "mps_available": mps_available, "device": device}


def git_info(repo_dir: Path | None = None) -> dict[str, Any]:
    """Best-effort git SHA and dirty flag; never raises when git or a repo is absent."""
    cwd = repo_dir or Path.cwd()
    try:
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return {"sha": None, "dirty": None}
    if sha_result.returncode != 0:
        return {"sha": None, "dirty": None}
    sha = sha_result.stdout.strip()
    dirty = bool(status_result.stdout.strip()) if status_result.returncode == 0 else None
    return {"sha": sha, "dirty": dirty}


def capture_env(repo_dir: Path | None = None) -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "forecheck_version": __version__,
        "packages": {name: _package_version(name) for name in _OPTIONAL_PACKAGES},
        "git": git_info(repo_dir),
        "hostname": socket.gethostname(),
        "device": _device_info(),
    }


def compute_data_hashes(data_dir: Path, splits: Iterable[Split]) -> dict[str, str]:
    """sha256 of each split's JSONL file, keyed by split name."""
    hashes: dict[str, str] = {}
    for split in splits:
        path = data_dir / f"{split.value}.jsonl"
        hashes[split.value] = sha256_file(path)
    return hashes


def write_run_capture(
    run_dir: Path, config: TrainConfig | EncoderTrainConfig, *, repo_dir: Path | None = None
) -> Path:
    """Write the resolved config, data hashes, prompt contract and env into ``run_dir``."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.resolved.yaml").write_text(config.to_yaml(), encoding="utf-8")
    splits = [config.data.train_split, config.data.dev_split]
    data_hashes = compute_data_hashes(config.data.dir, splits)
    (run_dir / "data_hashes.json").write_text(
        json.dumps(data_hashes, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "prompt_contract.json").write_text(
        json.dumps(
            capture_prompt_contract(strip_identity=config.data.strip_identity),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (run_dir / "env.json").write_text(
        json.dumps(capture_env(repo_dir), indent=2, sort_keys=True), encoding="utf-8"
    )
    return run_dir


def write_checkpoint_manifest(
    checkpoint_dir: Path,
    *,
    step: int,
    files: dict[str, str],
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write ``checkpoint_manifest.json`` describing one saved checkpoint.

    ``files`` maps a logical name (``"adapter"``, ``"optimizer"``, ``"scheduler"``,
    ``"rng"``) to the sha256 of the file written for it.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"step": step, "files": files}
    if extra:
        manifest.update(extra)
    path = checkpoint_dir / "checkpoint_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path
