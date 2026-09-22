from __future__ import annotations

from pathlib import Path

import pytest

from forecheck.contracts import (
    AgentIdentity,
    Example,
    LabelValue,
    PolicyStatement,
    Principal,
    RiskDimension,
    Split,
    UsageRestriction,
)
from forecheck.data.io import write_jsonl
from forecheck.training.dataset import (
    CONTEXT_BLOCK_ID,
    DIMENSION_ORDER,
    DataDisciplineError,
    TrainableExampleDataset,
    encode_example,
    load_examples,
)
from tests.training.conftest import FakeChatTokenizer, FakeTokenizer, make_training_example


def _make_identity_example(example_id: str = "ex-1") -> Example:
    """A training example whose context carries entitlements, delegated scopes,
    a delegation chain and policy text -- everything ``strip_identity`` should omit."""
    example = make_training_example(example_id)
    context = example.context.model_copy(
        update={
            "principal": Principal(id="user-1", entitlements=["billing:refund:<=500"]),
            "agent": AgentIdentity(
                id="agent-1", delegated_scopes=["billing:refund"], on_behalf_of="delegator-99"
            ),
            "policies": [
                PolicyStatement(id="pol-1", text="Refunds over $500 require manager approval.")
            ],
        }
    )
    return example.model_copy(update={"context": context})


def test_dimension_order_covers_every_risk_dimension() -> None:
    assert set(DIMENSION_ORDER) == set(RiskDimension)
    assert len(DIMENSION_ORDER) == 11


def test_load_examples_refuses_non_train_dev_splits(tmp_path: Path) -> None:
    with pytest.raises(DataDisciplineError, match="not usable for training"):
        load_examples(tmp_path, Split.CALIBRATION)
    with pytest.raises(DataDisciplineError, match="not usable for training"):
        load_examples(tmp_path, Split.TEST)


def test_load_examples_reads_the_split_named_jsonl_file(tmp_path: Path) -> None:
    example = make_training_example("ex-1", split=Split.TRAIN)
    write_jsonl(tmp_path / "train.jsonl", [example])

    loaded = load_examples(tmp_path, Split.TRAIN)

    assert [e.example_id for e in loaded] == ["ex-1"]


def test_load_examples_refuses_eval_only_rows(tmp_path: Path) -> None:
    example = make_training_example("ex-1", usage=UsageRestriction.EVAL_ONLY)
    write_jsonl(tmp_path / "train.jsonl", [example])

    with pytest.raises(DataDisciplineError, match="eval_only"):
        load_examples(tmp_path, Split.TRAIN)


def test_load_examples_refuses_canary_rows(tmp_path: Path) -> None:
    example = make_training_example("ex-1", canary_present=True)
    write_jsonl(tmp_path / "train.jsonl", [example])

    with pytest.raises(DataDisciplineError, match="canary"):
        load_examples(tmp_path, Split.TRAIN)


def test_shared_prefill_encodes_one_sequence_with_eleven_targets(
    fake_tokenizer: FakeTokenizer,
) -> None:
    example = make_training_example("ex-1")

    sequences = encode_example(example, fake_tokenizer, shared_prefill=True)

    assert len(sequences) == 1
    sequence = sequences[0]
    assert len(sequence.targets) == 11
    assert {t.dimension for t in sequence.targets} == set(RiskDimension)
    assert set(sequence.block_ids[: sequence.block_ids.index(1)]) == {CONTEXT_BLOCK_ID}
    for target in sequence.targets:
        assert 0 <= target.position < len(sequence.input_ids)


def test_naive_encodes_eleven_independent_sequences(fake_tokenizer: FakeTokenizer) -> None:
    example = make_training_example("ex-1")

    sequences = encode_example(example, fake_tokenizer, shared_prefill=False)

    assert len(sequences) == 11
    for sequence in sequences:
        assert len(sequence.targets) == 1
        assert set(sequence.block_ids) == {CONTEXT_BLOCK_ID}
        assert sequence.targets[0].position == len(sequence.input_ids) - 1


def test_shared_and_naive_encodings_produce_equivalent_targets(
    fake_tokenizer: FakeTokenizer,
) -> None:
    """Targets must match between the two encodings even though positions differ."""
    example = make_training_example(
        "ex-1", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.YES}
    )

    shared = encode_example(example, fake_tokenizer, shared_prefill=True)
    naive = encode_example(example, FakeTokenizer(), shared_prefill=False)

    shared_targets = {t.dimension: t.label for t in shared[0].targets}
    naive_targets = {seq.targets[0].dimension: seq.targets[0].label for seq in naive}

    assert shared_targets == naive_targets


def test_encode_example_raises_when_budget_exceeded(fake_tokenizer: FakeTokenizer) -> None:
    example = make_training_example("ex-1")

    with pytest.raises(DataDisciplineError, match="max_prompt_tokens"):
        encode_example(example, fake_tokenizer, shared_prefill=True, max_prompt_tokens=3)


def test_trainable_dataset_caches_encodings(fake_tokenizer: FakeTokenizer) -> None:
    examples = [make_training_example("ex-1"), make_training_example("ex-2")]
    dataset = TrainableExampleDataset(examples, fake_tokenizer)

    assert len(dataset) == 2
    first = dataset[0]
    second = dataset[0]
    assert first is second
    assert dataset[0][0].example_id == "ex-1"
    assert dataset[1][0].example_id == "ex-2"


def test_shared_prefill_chat_template_encodes_one_sequence_with_eleven_targets(
    fake_chat_tokenizer: FakeChatTokenizer,
) -> None:
    example = make_training_example("ex-1")

    sequences = encode_example(
        example, fake_chat_tokenizer, shared_prefill=True, use_chat_template=True
    )

    assert len(sequences) == 1
    sequence = sequences[0]
    assert len(sequence.targets) == 11
    assert {t.dimension for t in sequence.targets} == set(RiskDimension)
    assert set(sequence.block_ids[: sequence.block_ids.index(1)]) == {CONTEXT_BLOCK_ID}
    for target in sequence.targets:
        assert 0 <= target.position < len(sequence.input_ids)


def test_naive_chat_template_encodes_eleven_independent_sequences(
    fake_chat_tokenizer: FakeChatTokenizer,
) -> None:
    example = make_training_example("ex-1")

    sequences = encode_example(
        example, fake_chat_tokenizer, shared_prefill=False, use_chat_template=True
    )

    assert len(sequences) == 11
    for sequence in sequences:
        assert len(sequence.targets) == 1
        assert set(sequence.block_ids) == {CONTEXT_BLOCK_ID}
        assert sequence.targets[0].position == len(sequence.input_ids) - 1


def test_shared_and_naive_chat_template_encodings_produce_equivalent_targets(
    fake_chat_tokenizer: FakeChatTokenizer,
) -> None:
    example = make_training_example(
        "ex-1", label_overrides={RiskDimension.FINANCIAL_COMMITMENT: LabelValue.YES}
    )

    shared = encode_example(
        example, fake_chat_tokenizer, shared_prefill=True, use_chat_template=True
    )
    naive = encode_example(
        example, FakeChatTokenizer(), shared_prefill=False, use_chat_template=True
    )

    shared_targets = {t.dimension: t.label for t in shared[0].targets}
    naive_targets = {seq.targets[0].dimension: seq.targets[0].label for seq in naive}

    assert shared_targets == naive_targets


class _BoundaryMergingChatTokenizer:
    """Merges the second user turn's role marker (``>``) with an immediately
    following ``I`` into one token, simulating a role-header token that is not truly
    atomic -- exactly the case :func:`plan_chat_prefill` must detect and reject."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool = True,
        tokenize: bool = False,
        **kwargs: object,
    ) -> str:
        system, user_context, assistant_ack, user_question = (m["content"] for m in messages)
        text = f"{system}|{user_context}|{assistant_ack}|>{user_question}"
        if add_generation_prompt:
            text += "|GEN"
        return text

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ids: list[int] = []
        i = 0
        while i < len(text):
            if text[i : i + 2] == ">I":
                ids.append(-1)
                i += 2
                continue
            ids.append(ord(text[i]))
            i += 1
        return ids


def test_shared_prefill_chat_template_raises_on_unstable_boundary() -> None:
    example = make_training_example("ex-1")

    with pytest.raises(DataDisciplineError, match="chat-template prefix/suffix split"):
        encode_example(
            example,
            _BoundaryMergingChatTokenizer(),
            shared_prefill=True,
            use_chat_template=True,
        )


def test_naive_chat_template_is_unaffected_by_the_same_unstable_boundary() -> None:
    example = make_training_example("ex-1")

    sequences = encode_example(
        example,
        _BoundaryMergingChatTokenizer(),
        shared_prefill=False,
        use_chat_template=True,
    )

    assert len(sequences) == 11


def _has_token(tokenizer: FakeTokenizer, sequence_ids: tuple[int, ...], word: str) -> bool:
    token_id = tokenizer.encode(word, add_special_tokens=False)[0]
    return token_id in sequence_ids


def test_encode_example_strip_identity_true_omits_entitlements_scopes_and_policy_text(
    fake_tokenizer: FakeTokenizer,
) -> None:
    example = _make_identity_example()

    sequence = encode_example(example, fake_tokenizer, shared_prefill=True, strip_identity=True)[0]

    assert not _has_token(fake_tokenizer, sequence.input_ids, "billing:refund:&lt;=500")
    assert not _has_token(fake_tokenizer, sequence.input_ids, "billing:refund")
    assert not _has_token(fake_tokenizer, sequence.input_ids, "delegator-99")
    assert not _has_token(fake_tokenizer, sequence.input_ids, "approval.")


def test_encode_example_strip_identity_false_includes_entitlements_scopes_and_policy_text(
    fake_tokenizer: FakeTokenizer,
) -> None:
    example = _make_identity_example()

    sequence = encode_example(example, fake_tokenizer, shared_prefill=True, strip_identity=False)[0]

    assert _has_token(fake_tokenizer, sequence.input_ids, "billing:refund:&lt;=500")
    assert _has_token(fake_tokenizer, sequence.input_ids, "billing:refund")
    assert _has_token(fake_tokenizer, sequence.input_ids, "delegator-99")
    assert _has_token(fake_tokenizer, sequence.input_ids, "approval.")


def test_encode_example_strip_identity_defaults_to_false(fake_tokenizer: FakeTokenizer) -> None:
    example = _make_identity_example()

    default_sequence = encode_example(example, fake_tokenizer, shared_prefill=True)[0]
    explicit_sequence = encode_example(
        example, FakeTokenizer(), shared_prefill=True, strip_identity=False
    )[0]

    assert default_sequence.input_ids == explicit_sequence.input_ids


def test_trainable_example_dataset_threads_strip_identity(fake_tokenizer: FakeTokenizer) -> None:
    example = _make_identity_example()
    stripped_dataset = TrainableExampleDataset([example], fake_tokenizer, strip_identity=True)
    full_dataset = TrainableExampleDataset([example], FakeTokenizer(), strip_identity=False)

    stripped_sequence = stripped_dataset[0][0]
    full_sequence = full_dataset[0][0]

    assert not _has_token(fake_tokenizer, stripped_sequence.input_ids, "approval.")
    assert _has_token(full_dataset._tokenizer, full_sequence.input_ids, "approval.")
