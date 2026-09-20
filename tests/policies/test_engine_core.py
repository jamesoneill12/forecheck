"""Core engine behaviour: fail-closed defaults, combination, uncertainty, replay."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from forecheck.contracts import (
    Decision,
    Obligation,
    ObligationKind,
    RiskDimension,
    RuleKind,
    RuleMatch,
)
from forecheck.policies.dsl import PolicyBundle, Rule, UnknownAs
from forecheck.policies.engine import DeterministicPolicyEngine, combine_matched_rules
from forecheck.policies.loader import hash_bundle

from .conftest import make_classification, make_context


def _engine(**bundle_overrides: object) -> DeterministicPolicyEngine:
    defaults: dict[str, object] = {
        "bundle_id": "test-bundle",
        "version": 1,
        "dsl_version": "1.0",
        "description": "test",
        "default_decision": Decision.REVIEW,
        "rules": [],
    }
    defaults.update(bundle_overrides)
    bundle = PolicyBundle.model_validate(defaults)
    return DeterministicPolicyEngine(bundle, hash_bundle(bundle))


def _deny_rule(
    rule_id: str, dimension: RiskDimension, *, threshold: float = 0.5, hard: bool = True
) -> Rule:
    return Rule.model_validate(
        {
            "id": rule_id,
            "description": "deny rule",
            "decision": "deny",
            "hard": hard,
            "when": {"score": dimension.value, "gte": threshold},
        }
    )


def test_fail_closed_default_when_no_rule_matches() -> None:
    engine = _engine(default_decision=Decision.REVIEW, rules=[])
    classification = make_classification({RiskDimension.PROMPT_INJECTION_INFLUENCE: 0.01})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.REVIEW
    assert decision.matched_rules == []


def test_fail_closed_default_can_be_deny() -> None:
    engine = _engine(default_decision=Decision.DENY, rules=[])
    classification = make_classification({})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY


def test_rule_fires_and_reports_matched_on() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        rules=[_deny_rule("injection_deny", RiskDimension.PROMPT_INJECTION_INFLUENCE)],
    )
    classification = make_classification({RiskDimension.PROMPT_INJECTION_INFLUENCE: 0.91})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY
    assert len(decision.matched_rules) == 1
    match = decision.matched_rules[0]
    assert match.rule_id == "injection_deny"
    assert match.matched_on["prompt_injection_influence"] == "0.9100"
    assert "gte 0.5" in match.matched_on["prompt_injection_influence.threshold"]


def test_most_restrictive_wins_deny_beats_review_and_allow() -> None:
    matches = [
        RuleMatch(rule_id="a", decision=Decision.ALLOW, description="a"),
        RuleMatch(rule_id="r", decision=Decision.REVIEW, description="r"),
        RuleMatch(rule_id="d", decision=Decision.DENY, description="d"),
    ]
    assert combine_matched_rules(matches, Decision.ALLOW) is Decision.DENY


def test_most_restrictive_wins_review_beats_allow() -> None:
    matches = [
        RuleMatch(rule_id="a", decision=Decision.ALLOW, description="a"),
        RuleMatch(rule_id="r", decision=Decision.REVIEW, description="r"),
    ]
    assert combine_matched_rules(matches, Decision.ALLOW) is Decision.REVIEW


def test_allow_override_beats_non_hard_deny() -> None:
    matches = [
        RuleMatch(rule_id="d", decision=Decision.DENY, description="d", hard=False),
        RuleMatch(
            rule_id="o",
            decision=Decision.ALLOW,
            description="o",
            kind=RuleKind.ALLOW_OVERRIDE,
            obligations=[Obligation(kind=ObligationKind.LOG_TO_AUDIT_SINK)],
        ),
    ]
    assert combine_matched_rules(matches, Decision.REVIEW) is Decision.ALLOW


def test_allow_override_cannot_beat_hard_rule() -> None:
    matches = [
        RuleMatch(rule_id="d", decision=Decision.DENY, description="d", hard=True),
        RuleMatch(
            rule_id="o",
            decision=Decision.ALLOW,
            description="o",
            kind=RuleKind.ALLOW_OVERRIDE,
            obligations=[Obligation(kind=ObligationKind.LOG_TO_AUDIT_SINK)],
        ),
    ]
    assert combine_matched_rules(matches, Decision.REVIEW) is Decision.DENY


def test_no_matches_returns_default() -> None:
    assert combine_matched_rules([], Decision.REVIEW) is Decision.REVIEW
    assert combine_matched_rules([], Decision.ALLOW) is Decision.ALLOW


def test_replay_of_matched_rules_reproduces_decision() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        rules=[
            _deny_rule("hard_deny", RiskDimension.PRIVILEGE_ESCALATION, hard=True),
            Rule.model_validate(
                {
                    "id": "review_rule",
                    "description": "review",
                    "decision": "review",
                    "when": {"score": "policy_conflict", "gte": 0.3},
                }
            ),
        ],
    )
    classification = make_classification(
        {RiskDimension.PRIVILEGE_ESCALATION: 0.9, RiskDimension.POLICY_CONFLICT: 0.4}
    )
    decision = engine.evaluate(classification)
    replayed = combine_matched_rules(decision.matched_rules, engine.default_decision)
    assert replayed == decision.decision


def test_uncalibrated_without_opt_in_short_circuits_to_uncalibrated_decision() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        uncalibrated_decision=Decision.REVIEW,
        allow_uncalibrated=False,
        rules=[_deny_rule("would_fire", RiskDimension.PROMPT_INJECTION_INFLUENCE)],
    )
    classification = make_classification(
        calibrated=False, raw_scores={RiskDimension.PROMPT_INJECTION_INFLUENCE: 0.99}
    )
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.REVIEW
    assert decision.matched_rules == []


def test_uncalibrated_with_opt_in_uses_raw_scores_and_warns() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        allow_uncalibrated=True,
        rules=[_deny_rule("fires_on_raw", RiskDimension.PROMPT_INJECTION_INFLUENCE)],
    )
    classification = make_classification(
        calibrated=False, raw_scores={RiskDimension.PROMPT_INJECTION_INFLUENCE: 0.99}
    )
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY
    assert len(decision.matched_rules) == 1
    assert any(o.kind is ObligationKind.LOG_TO_AUDIT_SINK for o in decision.obligations)


def test_abstained_dimension_treated_as_worst_case_not_zero() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        unknown_as=UnknownAs.WORST_CASE,
        rules=[_deny_rule("deny_on_injection", RiskDimension.PROMPT_INJECTION_INFLUENCE)],
    )
    classification = make_classification(abstained=[RiskDimension.PROMPT_INJECTION_INFLUENCE])
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY


def test_abstained_dimension_with_zero_unknown_as_does_not_fire() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        unknown_as=UnknownAs.ZERO,
        rules=[_deny_rule("deny_on_injection", RiskDimension.PROMPT_INJECTION_INFLUENCE)],
    )
    classification = make_classification(abstained=[RiskDimension.PROMPT_INJECTION_INFLUENCE])
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.ALLOW


def test_allow_rule_does_not_fire_on_unknown_under_worst_case() -> None:
    override = Rule.model_validate(
        {
            "id": "allow_when_dev",
            "description": "allow",
            "decision": "allow",
            "kind": "allow_override",
            "when": {"fact": "stage", "is": "development"},
            "obligations": ["log_to_audit_sink"],
        }
    )
    engine = _engine(
        default_decision=Decision.REVIEW, unknown_as=UnknownAs.WORST_CASE, rules=[override]
    )
    classification = make_classification({})
    decision = engine.evaluate(classification, context=None)
    assert decision.decision is Decision.REVIEW
    assert decision.matched_rules == []


def test_missing_context_treats_facts_as_unknown_not_false() -> None:
    deny_when_fact_unknown_or_true = Rule.model_validate(
        {
            "id": "deny_on_freeze",
            "description": "deny",
            "decision": "deny",
            "hard": True,
            "when": {"fact": "change_freeze", "is": True},
        }
    )
    engine = _engine(
        default_decision=Decision.ALLOW,
        unknown_as=UnknownAs.WORST_CASE,
        rules=[deny_when_fact_unknown_or_true],
    )
    classification = make_classification({})
    decision = engine.evaluate(classification, context=None)
    assert decision.decision is Decision.DENY
    assert decision.matched_rules[0].matched_on["change_freeze"] == "unknown"


def test_context_supplied_known_false_fact_does_not_fire() -> None:
    deny_on_freeze = Rule.model_validate(
        {
            "id": "deny_on_freeze",
            "description": "deny",
            "decision": "deny",
            "hard": True,
            "when": {"fact": "change_freeze", "is": True},
        }
    )
    engine = _engine(default_decision=Decision.ALLOW, rules=[deny_on_freeze])
    classification = make_classification({})
    decision = engine.evaluate(classification, context=make_context())
    assert decision.decision is Decision.ALLOW


DIMENSION_STRATEGY = st.sampled_from(list(RiskDimension))


@st.composite
def _classification_strategy(
    draw: st.DrawFn,
) -> tuple[bool, dict[RiskDimension, float], list[RiskDimension]]:
    calibrated = draw(st.booleans())
    dimensions = draw(st.lists(DIMENSION_STRATEGY, unique=True, max_size=4))
    scores: dict[RiskDimension, float] = {}
    abstained: list[RiskDimension] = []
    for dimension in dimensions:
        if draw(st.booleans()):
            abstained.append(dimension)
        else:
            scores[dimension] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    return calibrated, scores, abstained


@given(
    payload=_classification_strategy(),
    use_context=st.booleans(),
    stage_is_production=st.booleans(),
    change_freeze=st.booleans(),
    unknown_as=st.sampled_from(list(UnknownAs)),
)
def test_evaluate_is_deterministic_and_total(
    payload: tuple[bool, dict[RiskDimension, float], list[RiskDimension]],
    use_context: bool,
    stage_is_production: bool,
    change_freeze: bool,
    unknown_as: UnknownAs,
) -> None:
    from forecheck.contracts import Environment, Stage

    calibrated, scores, abstained = payload
    engine = _engine(
        default_decision=Decision.REVIEW,
        allow_uncalibrated=True,
        unknown_as=unknown_as,
        rules=[
            _deny_rule("d1", RiskDimension.PROMPT_INJECTION_INFLUENCE, threshold=0.5),
            Rule.model_validate(
                {
                    "id": "r1",
                    "description": "r",
                    "decision": "review",
                    "when": {
                        "all": [
                            {"fact": "change_freeze", "is": True},
                            {"fact": "stage", "is": "production"},
                        ]
                    },
                }
            ),
        ],
    )
    context = (
        make_context(
            environment=Environment(
                stage=Stage.PRODUCTION if stage_is_production else Stage.DEVELOPMENT,
                change_freeze=change_freeze,
            )
        )
        if use_context
        else None
    )

    def run() -> Decision:
        classification = make_classification(scores, abstained=abstained, calibrated=calibrated)
        result = engine.evaluate(classification, context=context)
        assert result.decision in (Decision.ALLOW, Decision.REVIEW, Decision.DENY)
        return result.decision

    first = run()
    second = run()
    assert first == second
