from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import typer

from forecheck.cli_cmds.judge import agreement_command, label_command, sample_command
from forecheck.contracts import RiskDimension
from forecheck.data.io import write_jsonl
from forecheck.judge.providers import ProviderResponse
from forecheck.judge.schema import read_sample_rows
from tests.evaluation.conftest import all_no_labels, make_example


def _write_split(data_dir: Path, name: str, n: int) -> None:
    examples = [
        make_example(example_id=f"{name}-{i}", family_id=f"{name}-fam-{i}", labels=all_no_labels())
        for i in range(n)
    ]
    write_jsonl(data_dir / f"{name}.jsonl", examples)


def test_sample_command_writes_sample_and_coverage(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "heldout_family", 5)
    _write_split(data_dir, "heldout_policy_kind", 5)
    out_path = tmp_path / "out" / "sample.jsonl"

    sample_command(
        data=data_dir,
        splits="heldout_family,heldout_policy_kind",
        n=6,
        seed=0,
        out=out_path,
        cell_target=2,
    )

    rows = read_sample_rows(out_path)
    assert len(rows) == 6
    coverage = json.loads((out_path.parent / "coverage.json").read_text())
    assert coverage["n_selected"] == 6


def test_sample_command_rejects_missing_split(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "heldout_family", 3)

    with pytest.raises(typer.BadParameter, match="split file not found"):
        sample_command(
            data=data_dir,
            splits="heldout_family,does_not_exist",
            n=3,
            seed=0,
            out=tmp_path / "sample.jsonl",
        )


class _FakeProvider:
    def __init__(self, model: str) -> None:
        self.model = model

    def complete(self, *, system: str, user: str, client: httpx.Client) -> ProviderResponse:
        text = json.dumps({d.value: {"value": "no", "rationale": "ok"} for d in RiskDimension})
        return ProviderResponse(text=text, input_tokens=1, output_tokens=1)


def test_label_command_labels_and_reruns_are_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "forecheck.judge.labeling.provider_for_name",
        lambda name, model, **kwargs: _FakeProvider(model),
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_split(data_dir, "heldout_family", 4)
    sample_path = tmp_path / "sample.jsonl"
    sample_command(data=data_dir, splits="heldout_family", n=4, seed=0, out=sample_path)

    labels_path = tmp_path / "labels.jsonl"
    label_command(sample=sample_path, model="fake-v1", out=labels_path)
    first_out = capsys.readouterr().out
    assert "4 new, 0 cached" in first_out

    label_command(sample=sample_path, model="fake-v1", out=labels_path)
    second_out = capsys.readouterr().out
    assert "0 new, 4 cached" in second_out

    rows = labels_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 4


def test_agreement_command_writes_report_and_disagreements(tmp_path: Path) -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "forecheck.judge.labeling.provider_for_name",
            lambda name, model, **kwargs: _FakeProvider(model),
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        _write_split(data_dir, "heldout_family", 3)
        sample_path = tmp_path / "sample.jsonl"
        sample_command(data=data_dir, splits="heldout_family", n=3, seed=0, out=sample_path)
        labels_path = tmp_path / "labels.jsonl"
        label_command(sample=sample_path, model="fake-v1", out=labels_path)

    out_dir = tmp_path / "agreement"
    agreement_command(sample=sample_path, labels=labels_path, out=out_dir)

    assert (out_dir / "agreement.json").exists()
    assert (out_dir / "agreement.md").exists()
    assert (out_dir / "disagreements.jsonl").exists()
    report = json.loads((out_dir / "agreement.json").read_text())
    assert report["n_examples"] == 3
    for dim in RiskDimension:
        assert report["dimensions"][dim.value]["agreement_rate"] == pytest.approx(1.0)
