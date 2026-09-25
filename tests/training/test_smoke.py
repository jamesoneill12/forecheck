from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from forecheck.contracts import LabelValue, RiskDimension, Split
from forecheck.data.io import write_jsonl
from forecheck.training.smoke import build_smoke_config, build_synthetic_examples
from forecheck.training.smoke import test_smoke_cpu_train as test_smoke_cpu_train

__all__ = ["test_smoke_cpu_train"]

HAS_TORCH = importlib.util.find_spec("torch") is not None


def _write_dev_heavy_data(data_dir: Path, n_train: int, n_dev: int) -> None:
    train_examples = build_synthetic_examples(n_train, family_prefix="dev-cap-train")
    dev_examples = [
        example.model_copy(update={"split": Split.DEV})
        for example in build_synthetic_examples(n_dev, family_prefix="dev-cap-dev")
    ]
    write_jsonl(data_dir / "train.jsonl", train_examples)
    write_jsonl(data_dir / "dev.jsonl", dev_examples)


def test_build_synthetic_examples_are_valid_and_distinct() -> None:
    examples = build_synthetic_examples(6)

    assert len({e.example_id for e in examples}) == 6
    assert len({e.family_id for e in examples}) == 6
    for example in examples:
        assert example.split is Split.TRAIN
        assert set(example.labels.values) == set(RiskDimension)


def test_build_synthetic_examples_include_both_benign_and_risky_rows() -> None:
    examples = build_synthetic_examples(4)

    destructive = RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION
    labels = {e.labels.values[destructive] for e in examples}

    assert LabelValue.YES in labels
    assert LabelValue.NO in labels


@pytest.mark.slow
@pytest.mark.network
@pytest.mark.skipif(not HAS_TORCH, reason="forecheck[train] is not installed")
def test_dev_max_examples_caps_the_dev_dataset_seen_by_eval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import forecheck.training.loop as loop_module

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_dev_heavy_data(data_dir, n_train=4, n_dev=8)

    output_dir = tmp_path / "run"
    config = build_smoke_config(data_dir=data_dir, output_dir=output_dir, steps=2)
    config = config.model_copy(
        update={"data": config.data.model_copy(update={"dev_max_examples": 3})}
    )

    dev_sizes: list[int] = []
    original_evaluate = loop_module._evaluate

    def spy_evaluate(torch: object, model: object, dev_dataset: object, **kwargs: object) -> object:
        dev_sizes.append(len(dev_dataset))  # type: ignore[arg-type]
        return original_evaluate(torch, model, dev_dataset, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(loop_module, "_evaluate", spy_evaluate)

    loop_module.run_training(config)

    assert dev_sizes
    assert all(size <= 3 for size in dev_sizes)


def _saved_checkpoint_steps(output_dir: Path) -> set[int]:
    checkpoints_dir = output_dir / "checkpoints"
    return {int(p.name.removeprefix("step-")) for p in checkpoints_dir.iterdir() if p.is_dir()}


@pytest.mark.slow
@pytest.mark.network
@pytest.mark.skipif(not HAS_TORCH, reason="forecheck[train] is not installed")
def test_keep_checkpoints_prunes_to_n_most_recent_plus_best(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import forecheck.training.loop as loop_module

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_dev_heavy_data(data_dir, n_train=8, n_dev=4)

    output_dir = tmp_path / "run"
    config = build_smoke_config(data_dir=data_dir, output_dir=output_dir, steps=6)
    config = config.model_copy(
        update={
            "train": config.train.model_copy(
                update={
                    "eval_every": 2,
                    "save_every": 2,
                    "keep_checkpoints": 1,
                    "early_stop_patience": 100,
                }
            )
        }
    )

    # Best AUPRC lands on step 2; steps 4 and 6 must not evict it despite keep=1.
    auprc_by_call = iter([0.9, 0.5, 0.4])

    def fake_evaluate(*args: object, **kwargs: object) -> tuple[float, dict[object, object]]:
        return next(auprc_by_call), {}

    monkeypatch.setattr(loop_module, "_evaluate", fake_evaluate)

    loop_module.run_training(config)

    assert _saved_checkpoint_steps(output_dir) == {2, 6}


@pytest.mark.slow
@pytest.mark.network
@pytest.mark.skipif(not HAS_TORCH, reason="forecheck[train] is not installed")
def test_keep_checkpoints_unset_keeps_every_saved_checkpoint(tmp_path: Path) -> None:
    from forecheck.training.loop import run_training

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_dev_heavy_data(data_dir, n_train=8, n_dev=4)

    output_dir = tmp_path / "run"
    config = build_smoke_config(data_dir=data_dir, output_dir=output_dir, steps=6)
    config = config.model_copy(
        update={
            "train": config.train.model_copy(
                update={"eval_every": 2, "save_every": 2, "early_stop_patience": 100}
            )
        }
    )

    run_training(config)

    assert _saved_checkpoint_steps(output_dir) == {2, 4, 6}
