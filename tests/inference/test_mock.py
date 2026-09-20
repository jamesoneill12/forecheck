from __future__ import annotations

from forecheck.contracts import RiskDimension
from forecheck.inference.mock import MockBackend
from forecheck.inference.prompt import prompt_contract_hash
from tests.inference.conftest import destructive_context, injected_instruction_context, make_context


def test_model_info_declares_mock_and_not_production() -> None:
    backend = MockBackend(seed=0)
    info = backend.model_info
    assert info.backend == "mock"
    assert info.model_id == "mock-heuristic-v1"
    assert info.prompt_contract_hash == prompt_contract_hash()


def test_capabilities_are_deterministic() -> None:
    assert MockBackend(seed=0).capabilities.deterministic is True


def test_score_is_deterministic_for_same_context_and_seed() -> None:
    backend = MockBackend(seed=7)
    context = make_context()
    first = backend.score(context)
    second = backend.score(context)
    assert first.scores == second.scores


def test_different_seeds_produce_different_jitter() -> None:
    context = make_context()
    a = MockBackend(seed=1).score(context)
    b = MockBackend(seed=2).score(context)
    assert a.scores != b.scores


def test_all_scores_are_bounded_unit_interval() -> None:
    backend = MockBackend(seed=0)
    scores = backend.score(injected_instruction_context())
    for value in scores.scores.values():
        assert 0.0 <= value <= 1.0


def test_prompt_injection_heuristic_fires_on_matching_imperative_and_action() -> None:
    backend = MockBackend(seed=0)
    injected = backend.score(injected_instruction_context())
    benign = backend.score(make_context())
    assert (
        injected.scores[RiskDimension.PROMPT_INJECTION_INFLUENCE]
        > benign.scores[RiskDimension.PROMPT_INJECTION_INFLUENCE]
    )


def test_destructive_action_scores_higher_than_read_only() -> None:
    backend = MockBackend(seed=0)
    destructive = backend.score(destructive_context())
    benign = backend.score(make_context())
    assert (
        destructive.scores[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION]
        > benign.scores[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION]
    )


def test_score_batch_matches_sequential_scores() -> None:
    backend = MockBackend(seed=3)
    contexts = [make_context(), destructive_context()]
    batch = backend.score_batch(contexts)
    sequential = [backend.score(c) for c in contexts]
    assert [b.scores for b in batch] == [s.scores for s in sequential]


def test_only_requested_dimensions_are_scored() -> None:
    backend = MockBackend(seed=0)
    result = backend.score(make_context(), dimensions=[RiskDimension.FINANCIAL_COMMITMENT])
    assert set(result.scores) == {RiskDimension.FINANCIAL_COMMITMENT}
