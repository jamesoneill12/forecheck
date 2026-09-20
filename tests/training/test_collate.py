from __future__ import annotations

import numpy as np

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.training.collate import build_batch, build_block_diagonal_mask
from forecheck.training.dataset import EncodedSequence, QuestionTarget


def test_mask_shape_matches_sequence_length() -> None:
    block_ids = [0, 0, 0, 1, 1, 2, 2, 2]
    mask = build_block_diagonal_mask(block_ids)
    assert mask.shape == (len(block_ids), len(block_ids))
    assert mask.dtype == np.bool_


def test_every_position_may_attend_to_itself_and_context() -> None:
    block_ids = [0, 0, 1, 1, 2, 2]
    mask = build_block_diagonal_mask(block_ids)
    n = len(block_ids)
    for i in range(n):
        assert mask[i, i]
        for j in range(n):
            if block_ids[j] == 0 and j <= i:
                assert mask[i, j]


def test_question_two_cannot_see_question_one() -> None:
    block_ids = [0, 0, 1, 1, 2, 2]
    mask = build_block_diagonal_mask(block_ids)
    q2_positions = [i for i, b in enumerate(block_ids) if b == 2]
    q1_positions = [i for i, b in enumerate(block_ids) if b == 1]
    for i in q2_positions:
        for j in q1_positions:
            assert not mask[i, j], f"position {i} (Q2) must not attend to position {j} (Q1)"


def test_causality_still_holds_within_a_block() -> None:
    block_ids = [0, 1, 1, 1]
    mask = build_block_diagonal_mask(block_ids)
    assert not mask[1, 2]
    assert not mask[1, 3]
    assert mask[2, 1]
    assert mask[3, 1]
    assert mask[3, 2]


def _sequence(example_id: str, input_ids: list[int], block_ids: list[int]) -> EncodedSequence:
    target = QuestionTarget(
        dimension=RiskDimension.FINANCIAL_COMMITMENT,
        position=len(input_ids) - 1,
        label=LabelValue.YES,
    )
    return EncodedSequence(
        example_id=example_id,
        input_ids=tuple(input_ids),
        block_ids=tuple(block_ids),
        targets=(target,),
    )


def test_build_batch_pads_to_the_longest_sequence() -> None:
    short = _sequence("a", [1, 2, 3], [0, 0, 0])
    long = _sequence("b", [1, 2, 3, 4, 5], [0, 0, 0, 0, 0])

    batch = build_batch([short, long], pad_token_id=99)

    assert batch.input_ids.shape == (2, 5)
    assert list(batch.input_ids[0]) == [1, 2, 3, 99, 99]
    assert list(batch.input_ids[1]) == [1, 2, 3, 4, 5]
    assert batch.keep_mask.shape == (2, 1, 5, 5)


def test_build_batch_pad_columns_are_never_attendable() -> None:
    short = _sequence("a", [1, 2, 3], [0, 0, 0])
    long = _sequence("b", [1, 2, 3, 4, 5], [0, 0, 0, 0, 0])

    batch = build_batch([short, long], pad_token_id=99)

    for real_row in range(3):
        for pad_col in range(3, 5):
            assert not batch.keep_mask[0, 0, real_row, pad_col]


def test_build_batch_collects_targets_across_examples() -> None:
    short = _sequence("a", [1, 2, 3], [0, 0, 0])
    long = _sequence("b", [1, 2, 3, 4, 5], [0, 0, 0, 0, 0])

    batch = build_batch([short, long], pad_token_id=99)

    assert list(batch.target_batch_index) == [0, 1]
    assert list(batch.target_position) == [2, 4]
    assert batch.target_dimension == (
        RiskDimension.FINANCIAL_COMMITMENT,
        RiskDimension.FINANCIAL_COMMITMENT,
    )
