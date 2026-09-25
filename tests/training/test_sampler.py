from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from forecheck.training.loop import SeededEpochSampler, _prune_checkpoints, subsample_examples


def test_loop_module_imports_without_torch() -> None:
    from forecheck.training import loop

    assert hasattr(loop, "run_training")
    assert hasattr(loop, "SeededEpochSampler")


def test_same_seed_gives_the_same_epoch_order() -> None:
    a = SeededEpochSampler(20, seed=42)
    b = SeededEpochSampler(20, seed=42)

    assert a.epoch_indices(0) == b.epoch_indices(0)
    assert a.epoch_indices(3) == b.epoch_indices(3)


def test_different_seeds_give_different_epoch_order() -> None:
    a = SeededEpochSampler(20, seed=1)
    b = SeededEpochSampler(20, seed=2)

    assert a.epoch_indices(0) != b.epoch_indices(0)


def test_different_epochs_give_different_order_for_the_same_sampler() -> None:
    sampler = SeededEpochSampler(20, seed=0)

    assert sampler.epoch_indices(0) != sampler.epoch_indices(1)


def test_epoch_indices_is_a_permutation() -> None:
    sampler = SeededEpochSampler(15, seed=7)

    assert sorted(sampler.epoch_indices(0)) == list(range(15))


def test_shuffle_false_yields_identity_order() -> None:
    sampler = SeededEpochSampler(5, seed=123, shuffle=False)

    assert sampler.epoch_indices(0) == [0, 1, 2, 3, 4]
    assert sampler.epoch_indices(1) == [0, 1, 2, 3, 4]


def test_resuming_from_a_step_offset_replays_the_exact_suffix() -> None:
    sampler = SeededEpochSampler(10, seed=5)
    batch_size = 3
    n_epochs = 4

    fresh = list(sampler.batches(n_epochs, batch_size, resume_from_step=0))
    resumed = list(sampler.batches(n_epochs, batch_size, resume_from_step=2))

    assert resumed == fresh[2:]


def test_resuming_past_the_end_yields_nothing() -> None:
    sampler = SeededEpochSampler(10, seed=5)

    remaining = list(sampler.batches(1, 3, resume_from_step=1000))

    assert remaining == []


def test_n_examples_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        SeededEpochSampler(0, seed=0)


def test_batches_never_exceed_batch_size() -> None:
    sampler = SeededEpochSampler(7, seed=0)
    batches = list(sampler.batches(2, batch_size=3))

    assert all(0 < len(b) <= 3 for b in batches)
    flat = list(itertools.chain.from_iterable(batches))
    assert sorted(flat[:7]) == list(range(7))


def test_subsample_examples_returns_all_when_max_is_none() -> None:
    examples = list(range(10))

    assert subsample_examples(examples, None, seed=0) == examples


def test_subsample_examples_returns_all_when_under_the_cap() -> None:
    examples = list(range(5))

    assert subsample_examples(examples, 10, seed=0) == examples


def test_subsample_examples_caps_the_result_size() -> None:
    examples = list(range(100))

    subsample = subsample_examples(examples, 10, seed=0)

    assert len(subsample) == 10
    assert set(subsample) <= set(examples)


def test_subsample_examples_is_deterministic_for_the_same_seed() -> None:
    examples = list(range(100))

    a = subsample_examples(examples, 10, seed=7)
    b = subsample_examples(examples, 10, seed=7)

    assert a == b


def test_subsample_examples_differs_across_seeds() -> None:
    examples = list(range(100))

    a = subsample_examples(examples, 10, seed=1)
    b = subsample_examples(examples, 10, seed=2)

    assert a != b


def _make_checkpoint_dirs(run_dir: Path, steps: list[int]) -> None:
    for step in steps:
        (run_dir / "checkpoints" / f"step-{step}").mkdir(parents=True)


def _remaining_steps(run_dir: Path) -> set[int]:
    return {
        int(p.name.removeprefix("step-")) for p in (run_dir / "checkpoints").iterdir() if p.is_dir()
    }


def test_prune_checkpoints_keeps_only_n_most_recent(tmp_path: Path) -> None:
    _make_checkpoint_dirs(tmp_path, [10, 20, 30, 40, 50])

    _prune_checkpoints(tmp_path, keep=2, best_step=None)

    assert _remaining_steps(tmp_path) == {40, 50}


def test_prune_checkpoints_never_deletes_the_best_step(tmp_path: Path) -> None:
    _make_checkpoint_dirs(tmp_path, [10, 20, 30, 40, 50])

    _prune_checkpoints(tmp_path, keep=2, best_step=10)

    assert _remaining_steps(tmp_path) == {10, 40, 50}


def test_prune_checkpoints_is_a_noop_when_best_step_already_in_the_kept_window(
    tmp_path: Path,
) -> None:
    _make_checkpoint_dirs(tmp_path, [10, 20, 30])

    _prune_checkpoints(tmp_path, keep=2, best_step=30)

    assert _remaining_steps(tmp_path) == {20, 30}


def test_prune_checkpoints_handles_missing_checkpoints_dir(tmp_path: Path) -> None:
    _prune_checkpoints(tmp_path, keep=2, best_step=None)

    assert not (tmp_path / "checkpoints").exists()
