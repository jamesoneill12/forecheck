from __future__ import annotations

from pathlib import Path

import yaml

from forecheck.cli_cmds.data import generate, split
from forecheck.contracts import DatasetManifest


def _write_config(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "seed": 1234,
                "families": ["email_messaging"],
                "n_per_family": 40,
                "pairs_per_axis": 0,
            }
        ),
        encoding="utf-8",
    )


def test_split_default_withholds_four_policy_kinds(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    generate(config=config_path, out=out_dir)
    split(out_dir)
    manifest_paths = list(out_dir.glob("*.manifest.json"))
    assert manifest_paths
    manifest = DatasetManifest.model_validate_json(manifest_paths[0].read_text(encoding="utf-8"))
    assert len(manifest.heldout_policy_kinds) == 4


def test_split_honours_n_heldout_policy_kinds_option(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    generate(config=config_path, out=out_dir)
    split(out_dir, n_heldout_policy_kinds=6)
    manifest_paths = list(out_dir.glob("*.manifest.json"))
    manifest = DatasetManifest.model_validate_json(manifest_paths[0].read_text(encoding="utf-8"))
    assert len(manifest.heldout_policy_kinds) == 6
    assert manifest.heldout_policy_kinds == sorted(manifest.heldout_policy_kinds)
