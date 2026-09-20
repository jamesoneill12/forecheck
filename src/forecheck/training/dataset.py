"""``Example`` rows -> tokenized sequences with per-question answer targets.

Two encodings are supported, selected by ``train.shared_prefill``:

* **Shared prefill** (default): one sequence per example, ``[context][Q1][Q2]...[Q11]``.
  Each question's answer target sits at the last token position of that question's own
  span, mirroring exactly how :class:`forecheck.inference.hf.HFBackend` reads logits at
  the final position of a question appended to a shared, cached prefix. ``block_ids``
  tags every token with which block it belongs to (``0`` = context, ``1..11`` = the
  i-th question) for :mod:`forecheck.training.collate`'s block-diagonal attention mask.
* **Naive fallback** (``shared_prefill: false``): eleven independent sequences per
  example, each ``[context][Qi]``, matching the non-cached branch of the HF backend.

Only :data:`forecheck.contracts.Split.TRAIN` and :data:`forecheck.contracts.Split.DEV`
may be loaded here (``training/`` must never read ``calibration`` or ``test``, per
``docs/architecture.md`` §4), and any row whose licence is ``eval_only`` or carries a
canary is refused rather than silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from forecheck.contracts import Example, LabelValue, Limits, RiskDimension, Split, UsageRestriction
from forecheck.data.io import read_jsonl
from forecheck.inference.prompt import QUESTIONS
from forecheck.inference.serialization import render_context

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

__all__ = [
    "CONTEXT_BLOCK_ID",
    "DIMENSION_ORDER",
    "DataDisciplineError",
    "EncodedSequence",
    "QuestionTarget",
    "TokenizerLike",
    "TrainableExampleDataset",
    "encode_example",
    "load_examples",
]

_QUESTION_SEPARATOR = "\n\n"
_TRAINABLE_SPLITS: frozenset[Split] = frozenset({Split.TRAIN, Split.DEV})

CONTEXT_BLOCK_ID = 0
DIMENSION_ORDER: tuple[RiskDimension, ...] = tuple(RiskDimension)


class DataDisciplineError(RuntimeError):
    """A row or split is not permitted on the training data path."""


class TokenizerLike(Protocol):
    """The minimal surface :mod:`transformers` tokenizers provide that this module needs."""

    def encode(self, text: str, add_special_tokens: bool = True) -> Sequence[int]: ...


@dataclass(frozen=True, slots=True)
class QuestionTarget:
    dimension: RiskDimension
    position: int
    label: LabelValue


@dataclass(frozen=True, slots=True)
class EncodedSequence:
    example_id: str
    input_ids: tuple[int, ...]
    block_ids: tuple[int, ...]
    targets: tuple[QuestionTarget, ...]


def _check_license(example: Example) -> None:
    if example.license.usage is UsageRestriction.EVAL_ONLY:
        raise DataDisciplineError(
            f"example {example.example_id!r} is usage=eval_only and cannot be used for training"
        )
    if example.license.canary_present:
        raise DataDisciplineError(
            f"example {example.example_id!r} carries a canary and cannot be used for training"
        )


def load_examples(data_dir: Path, split: Split) -> list[Example]:
    """Load one split's JSONL file, refusing anything other than ``train``/``dev``."""
    if split not in _TRAINABLE_SPLITS:
        allowed = sorted(s.value for s in _TRAINABLE_SPLITS)
        raise DataDisciplineError(
            f"split {split.value!r} is not usable for training; only {allowed} are allowed"
        )
    path = data_dir / f"{split.value}.jsonl"
    examples = read_jsonl(path)
    for example in examples:
        _check_license(example)
    return examples


def _question_ids(tokenizer: TokenizerLike, dimension: RiskDimension) -> list[int]:
    return list(tokenizer.encode(_QUESTION_SEPARATOR + QUESTIONS[dimension]))


def _check_budget(example_id: str, n_tokens: int, max_prompt_tokens: int) -> None:
    if n_tokens > max_prompt_tokens:
        raise DataDisciplineError(
            f"example {example_id!r} encodes to {n_tokens} tokens, exceeding "
            f"data.max_prompt_tokens={max_prompt_tokens}"
        )


def _encode_shared(
    example: Example, tokenizer: TokenizerLike, context_ids: list[int], max_prompt_tokens: int
) -> EncodedSequence:
    input_ids = list(context_ids)
    block_ids = [CONTEXT_BLOCK_ID] * len(context_ids)
    targets: list[QuestionTarget] = []
    for block_index, dimension in enumerate(DIMENSION_ORDER, start=1):
        q_ids = _question_ids(tokenizer, dimension)
        input_ids.extend(q_ids)
        block_ids.extend([block_index] * len(q_ids))
        targets.append(
            QuestionTarget(
                dimension=dimension,
                position=len(input_ids) - 1,
                label=example.labels.values[dimension],
            )
        )
    _check_budget(example.example_id, len(input_ids), max_prompt_tokens)
    return EncodedSequence(
        example_id=example.example_id,
        input_ids=tuple(input_ids),
        block_ids=tuple(block_ids),
        targets=tuple(targets),
    )


def _encode_naive(
    example: Example,
    tokenizer: TokenizerLike,
    context_ids: list[int],
    dimension: RiskDimension,
    max_prompt_tokens: int,
) -> EncodedSequence:
    input_ids = list(context_ids) + _question_ids(tokenizer, dimension)
    _check_budget(example.example_id, len(input_ids), max_prompt_tokens)
    target = QuestionTarget(
        dimension=dimension,
        position=len(input_ids) - 1,
        label=example.labels.values[dimension],
    )
    return EncodedSequence(
        example_id=example.example_id,
        input_ids=tuple(input_ids),
        block_ids=tuple([CONTEXT_BLOCK_ID] * len(input_ids)),
        targets=(target,),
    )


def encode_example(
    example: Example,
    tokenizer: TokenizerLike,
    *,
    shared_prefill: bool = True,
    max_prompt_tokens: int = Limits.MAX_PROMPT_TOKENS,
) -> list[EncodedSequence]:
    """Encode one example: one sequence if ``shared_prefill``, else eleven.

    The eleven per-dimension targets carry every :class:`~forecheck.contracts.LabelValue`
    unchanged, including ``NOT_APPLICABLE``/``UNDETERMINED``; masking those out of the
    loss is :mod:`forecheck.training.loss`'s job, not this module's.
    """
    context_text = render_context(example.context)
    context_ids = list(tokenizer.encode(context_text))
    if shared_prefill:
        return [_encode_shared(example, tokenizer, context_ids, max_prompt_tokens)]
    return [
        _encode_naive(example, tokenizer, context_ids, dimension, max_prompt_tokens)
        for dimension in DIMENSION_ORDER
    ]


class TrainableExampleDataset:
    """A thin, torch-free sequence of :class:`Example` rows plus their encodings.

    Encoding is done lazily and cached per index so a single pass over a large split
    does not re-render context text on every epoch.
    """

    def __init__(
        self,
        examples: list[Example],
        tokenizer: TokenizerLike,
        *,
        shared_prefill: bool = True,
        max_prompt_tokens: int = Limits.MAX_PROMPT_TOKENS,
    ) -> None:
        self._examples = examples
        self._tokenizer = tokenizer
        self._shared_prefill = shared_prefill
        self._max_prompt_tokens = max_prompt_tokens
        self._cache: dict[int, list[EncodedSequence]] = {}

    def __len__(self) -> int:
        return len(self._examples)

    def __getitem__(self, index: int) -> list[EncodedSequence]:
        cached = self._cache.get(index)
        if cached is not None:
            return cached
        encoded = encode_example(
            self._examples[index],
            self._tokenizer,
            shared_prefill=self._shared_prefill,
            max_prompt_tokens=self._max_prompt_tokens,
        )
        self._cache[index] = encoded
        return encoded

    @property
    def examples(self) -> list[Example]:
        return self._examples
