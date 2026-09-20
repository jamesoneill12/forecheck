from __future__ import annotations

import itertools

import pytest

from forecheck.training.loop import SeededEpochSampler


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
