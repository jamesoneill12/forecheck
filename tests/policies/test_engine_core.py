"""Core engine behaviour: fail-closed defaults, combination, uncertainty, replay."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from forecheck.contracts import (
    Decision,
    DecisionMode,
    Obligation,
    ObligationKind,
    RiskDimension,
    RuleKind,
    RuleMatch,
)
from forecheck.policies.dsl import Cost, PolicyBundle, Rule, UnknownAs
from forecheck.policies.engine import (
    DeterministicPolicyEngine,
    combine_matched_rules,
    expected_costs,
)
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


def _expected_cost_engine(
    rules: list[Rule], *, default_decision: Decision = Decision.REVIEW
) -> DeterministicPolicyEngine:
    bundle = PolicyBundle.model_validate(
        {
            "bundle_id": "ec-bundle",
            "version": 1,
            "dsl_version": "1.1",
            "description": "test",
            "default_decision": default_decision,
            "decision_mode": "expected_cost",
            "rules": rules,
        }
    )
    return DeterministicPolicyEngine(bundle, hash_bundle(bundle))


_SYMMETRIC = Cost(allow_if_risky=1.0, review=10.0, deny_if_benign=1.0)


def _cost_rule(rule_id: str, dimension: RiskDimension, *, cost: Cost, hard: bool = False) -> Rule:
    return Rule.model_validate(
        {
            "id": rule_id,
            "description": "test",
            "decision": "deny" if hard else "review",
            "hard": hard,
            "when": {"score": dimension.value, "gte": 0.9 if hard else 0.0001},
            "cost": cost.model_dump(),
        }
    )


def test_expected_cost_picks_allow_when_cheapest() -> None:
    engine = _expected_cost_engine(
        [_cost_rule("r1", RiskDimension.FINANCIAL_COMMITMENT, cost=_SYMMETRIC)]
    )
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.1})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.ALLOW
    assert decision.decision_trace is not None
    assert decision.decision_trace.mode is DecisionMode.EXPECTED_COST


def test_expected_cost_picks_deny_when_cheapest() -> None:
    engine = _expected_cost_engine(
        [_cost_rule("r1", RiskDimension.FINANCIAL_COMMITMENT, cost=_SYMMETRIC)]
    )
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.9})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY


def test_expected_cost_tie_breaks_to_more_restrictive() -> None:
    engine = _expected_cost_engine(
        [_cost_rule("r1", RiskDimension.FINANCIAL_COMMITMENT, cost=_SYMMETRIC)]
    )
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.5})
    decision = engine.evaluate(classification)
    trace = decision.decision_trace
    assert trace is not None
    assert trace.expected_cost_allow == trace.expected_cost_deny
    assert decision.decision is Decision.DENY


def test_expected_cost_hard_rule_forces_deny_over_a_cheaper_allow_argmin() -> None:
    cheap_allow_expensive_deny = Cost(allow_if_risky=0.01, review=5.0, deny_if_benign=5.0)
    engine = _expected_cost_engine(
        [
            _cost_rule(
                "hard_but_cheap_argmin",
                RiskDimension.FINANCIAL_COMMITMENT,
                cost=cheap_allow_expensive_deny,
                hard=True,
            )
        ]
    )
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.95})
    decision = engine.evaluate(classification)
    assert decision.decision is Decision.DENY
    trace = decision.decision_trace
    assert trace is not None
    assert trace.argmin_decision is Decision.ALLOW
    assert trace.hard_override_applied is True


def test_expected_cost_decision_trace_matches_expected_costs_helper() -> None:
    rules = [_cost_rule("r1", RiskDimension.FINANCIAL_COMMITMENT, cost=_SYMMETRIC)]
    engine = _expected_cost_engine(rules)
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.3})
    decision = engine.evaluate(classification)
    costs = expected_costs(engine.bundle, classification)
    trace = decision.decision_trace
    assert trace is not None
    assert trace.expected_cost_allow == costs.allow
    assert trace.expected_cost_review == costs.review
    assert trace.expected_cost_deny == costs.deny


def test_threshold_mode_bundle_has_no_decision_trace() -> None:
    engine = _engine(
        default_decision=Decision.ALLOW,
        rules=[_deny_rule("d", RiskDimension.FINANCIAL_COMMITMENT)],
    )
    classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.9})
    decision = engine.evaluate(classification)
    assert decision.decision_trace is None


def test_expected_cost_abstained_dimension_contributes_nothing() -> None:
    rules = [
        _cost_rule("r1", RiskDimension.FINANCIAL_COMMITMENT, cost=_SYMMETRIC),
        _cost_rule("r2", RiskDimension.PRIVILEGE_ESCALATION, cost=_SYMMETRIC),
    ]
    engine = _expected_cost_engine(rules)
    classification = make_classification(
        {RiskDimension.FINANCIAL_COMMITMENT: 0.1},
        abstained=[RiskDimension.PRIVILEGE_ESCALATION],
    )
    decision = engine.evaluate(classification)
    solo_engine = _expected_cost_engine([rules[0]])
    solo_classification = make_classification({RiskDimension.FINANCIAL_COMMITMENT: 0.1})
    solo_decision = solo_engine.evaluate(solo_classification)
    assert decision.decision_trace is not None
    assert solo_decision.decision_trace is not None
    assert (
        decision.decision_trace.expected_cost_allow
        == solo_decision.decision_trace.expected_cost_allow
    )


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
