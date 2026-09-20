"""Padding and the block-diagonal attention mask for shared-prefill batches.

Built entirely on ``numpy`` so the mask logic is unit-testable without ``torch``
installed. :mod:`forecheck.training.loop` converts the boolean "keep" mask this module
produces into whatever additive-bias tensor the loaded model's attention
implementation expects, once torch is actually available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.training.dataset import CONTEXT_BLOCK_ID, EncodedSequence

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = ["Batch", "build_batch", "build_block_diagonal_mask"]


def build_block_diagonal_mask(
    block_ids: Sequence[int], *, context_block: int = CONTEXT_BLOCK_ID
) -> NDArray[np.bool_]:
    """A ``(seq, seq)`` boolean mask: ``mask[i, j]`` is True iff position ``i`` may
    attend to position ``j``.

    Attention is causal (``j <= i``) and, among the causal positions, allowed only when
    ``j`` is in the shared context block or in the same question block as ``i``. This is
    what stops question 2 from attending to question 1's tokens while still letting
    every question see the context computed once for the whole example.
    """
    n = len(block_ids)
    blocks = np.asarray(block_ids)
    causal = np.tril(np.ones((n, n), dtype=bool))
    same_block = blocks[:, None] == blocks[None, :]
    key_is_context = (blocks == context_block)[None, :]
    mask: NDArray[np.bool_] = causal & (same_block | key_is_context)
    return mask


@dataclass(frozen=True, slots=True)
class Batch:
    input_ids: NDArray[np.int64]
    keep_mask: NDArray[np.bool_]
    lengths: NDArray[np.int64]
    target_batch_index: NDArray[np.int64]
    target_position: NDArray[np.int64]
    target_dimension: tuple[RiskDimension, ...]
    target_label: tuple[LabelValue, ...]


def build_batch(
    sequences: Sequence[EncodedSequence],
    *,
    pad_token_id: int,
    context_block: int = CONTEXT_BLOCK_ID,
) -> Batch:
    """Right-pad ``sequences`` to a common length and build the per-example keep-masks.

    Padding columns are excluded from every real row's keep-mask; the diagonal is
    always kept so a padded row never softmaxes over an all-False mask.
    """
    if not sequences:
        raise ValueError("cannot build a batch from zero sequences")
    lengths = [len(seq.input_ids) for seq in sequences]
    max_len = max(lengths)
    batch_size = len(sequences)

    input_ids = np.full((batch_size, max_len), pad_token_id, dtype=np.int64)
    keep_mask = np.zeros((batch_size, 1, max_len, max_len), dtype=np.bool_)
    target_batch_index: list[int] = []
    target_position: list[int] = []
    target_dimension: list[RiskDimension] = []
    target_label: list[LabelValue] = []

    for b, seq in enumerate(sequences):
        n = lengths[b]
        input_ids[b, :n] = np.asarray(seq.input_ids, dtype=np.int64)
        block_mask = build_block_diagonal_mask(seq.block_ids, context_block=context_block)
        padded = np.zeros((max_len, max_len), dtype=np.bool_)
        padded[:n, :n] = block_mask
        np.fill_diagonal(padded, True)
        keep_mask[b, 0] = padded
        for target in seq.targets:
            target_batch_index.append(b)
            target_position.append(target.position)
            target_dimension.append(target.dimension)
            target_label.append(target.label)

    return Batch(
        input_ids=input_ids,
        keep_mask=keep_mask,
        lengths=np.asarray(lengths, dtype=np.int64),
        target_batch_index=np.asarray(target_batch_index, dtype=np.int64),
        target_position=np.asarray(target_position, dtype=np.int64),
        target_dimension=tuple(target_dimension),
        target_label=tuple(target_label),
    )
