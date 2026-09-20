from __future__ import annotations

from forecheck.contracts import RiskDimension
from forecheck.inference.prompt import (
    PROMPT_CONTRACT_HASH,
    QUESTIONS,
    SECTION_ORDER,
    prompt_contract_hash,
)


def test_hash_is_deterministic_and_matches_module_constant() -> None:
    assert prompt_contract_hash() == PROMPT_CONTRACT_HASH
    assert prompt_contract_hash() == prompt_contract_hash()


def test_hash_is_a_sha256_hex_digest() -> None:
    assert len(PROMPT_CONTRACT_HASH) == 64
    int(PROMPT_CONTRACT_HASH, 16)


def test_every_risk_dimension_has_a_question() -> None:
    for dimension in RiskDimension:
        assert dimension in QUESTIONS
        assert QUESTIONS[dimension].strip().endswith("?")


def test_questions_are_phrased_descriptively_not_normatively() -> None:
    normative_words = ("dangerous", "bad", "risky", "should you", "is it wrong")
    for question in QUESTIONS.values():
        lowered = question.lower()
        assert not any(word in lowered for word in normative_words)


def test_section_order_is_a_fixed_nonempty_tuple() -> None:
    assert len(SECTION_ORDER) == len(set(SECTION_ORDER))
    assert "proposed_action" in SECTION_ORDER
    assert "principal" in SECTION_ORDER
