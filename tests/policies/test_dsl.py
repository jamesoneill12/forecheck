"""Structural validation of the policy DSL schema itself."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from forecheck.contracts import Decision, DecisionMode, ObligationKind, RiskDimension, RuleKind
from forecheck.policies.dsl import (
    CRITICAL_COST_DIMENSIONS,
    HIGH_COST_DIMENSIONS,
    Condition,
    Cost,
    PolicyBundle,
    Rule,
    default_cost_for_dimension,
)


def _bundle(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "bundle_id": "test",
        "version": 1,
        "dsl_version": "1.0",
        "description": "test bundle",
        "default_decision": "review",
        "rules": [],
    }
    base.update(overrides)
    return base


def test_condition_requires_exactly_one_kind() -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate({})
    with pytest.raises(ValidationError):
        Condition.model_validate(
            {"score": "prompt_injection_influence", "gte": 0.5, "fact": "stage", "is": "production"}
        )


def test_score_condition_requires_a_threshold() -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate({"score": "prompt_injection_influence"})


def test_fact_condition_requires_a_comparator() -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate({"fact": "stage"})


def test_unknown_risk_dimension_is_a_load_error() -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate({"score": "not_a_real_dimension", "gte": 0.5})


def test_all_and_any_reject_empty_children() -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate({"all": []})
    with pytest.raises(ValidationError):
        Condition.model_validate({"any": []})


def test_nested_condition_tree_round_trips() -> None:
    condition = Condition.model_validate(
        {
            "all": [
                {"score": "prompt_injection_influence", "gte": 0.5},
                {"not": {"fact": "operation_is_mutating", "is": False}},
                {
                    "any": [
                        {"fact": "stage", "is": "production"},
                        {"fact": "change_freeze", "is": True},
                    ]
                },
            ]
        }
    )
    assert condition.all_ is not None
    assert len(condition.all_) == 3


def test_allow_override_requires_allow_decision() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "id": "bad",
                "description": "d",
                "decision": "deny",
                "kind": "allow_override",
                "when": {"fact": "stage", "is": "development"},
                "obligations": ["log_to_audit_sink"],
            }
        )


def test_allow_override_requires_obligations() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "id": "bad",
                "description": "d",
                "decision": "allow",
                "kind": "allow_override",
                "when": {"fact": "stage", "is": "development"},
            }
        )


def test_allow_override_cannot_be_hard() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "id": "bad",
                "description": "d",
                "decision": "allow",
                "kind": "allow_override",
                "hard": True,
                "when": {"fact": "stage", "is": "development"},
                "obligations": ["log_to_audit_sink"],
            }
        )


def test_valid_allow_override_rule() -> None:
    rule = Rule.model_validate(
        {
            "id": "ok",
            "description": "d",
            "decision": "allow",
            "kind": "allow_override",
            "when": {"fact": "stage", "is": "development"},
            "obligations": ["log_to_audit_sink"],
        }
    )
    assert rule.kind is RuleKind.ALLOW_OVERRIDE
    assert rule.decision is Decision.ALLOW
    assert rule.obligations == [ObligationKind.LOG_TO_AUDIT_SINK]


def test_bundle_rejects_duplicate_rule_ids() -> None:
    rule = {
        "id": "dup",
        "description": "d",
        "decision": "review",
        "when": {"score": "policy_conflict", "gte": 0.5},
    }
    with pytest.raises(ValidationError):
        PolicyBundle.model_validate(_bundle(rules=[rule, dict(rule)]))


def test_bundle_defaults() -> None:
    bundle = PolicyBundle.model_validate(_bundle())
    assert bundle.default_decision is Decision.REVIEW
    assert bundle.uncalibrated_decision is Decision.REVIEW
    assert bundle.allow_uncalibrated is False


def test_score_condition_accepts_every_risk_dimension() -> None:
    for dimension in RiskDimension:
        Condition.model_validate({"score": dimension.value, "gte": 0.1})


def test_bundle_decision_mode_defaults_to_threshold() -> None:
    bundle = PolicyBundle.model_validate(_bundle())
    assert bundle.decision_mode is DecisionMode.THRESHOLD


def test_bundle_decision_mode_expected_cost_round_trips() -> None:
    bundle = PolicyBundle.model_validate(_bundle(decision_mode="expected_cost"))
    assert bundle.decision_mode is DecisionMode.EXPECTED_COST


def test_rule_cost_defaults_to_none() -> None:
    rule = Rule.model_validate(
        {
            "id": "r",
            "description": "d",
            "decision": "review",
            "when": {"score": "policy_conflict", "gte": 0.5},
        }
    )
    assert rule.cost is None


def test_rule_cost_parses_and_round_trips() -> None:
    rule = Rule.model_validate(
        {
            "id": "r",
            "description": "d",
            "decision": "review",
            "when": {"score": "policy_conflict", "gte": 0.5},
            "cost": {"allow_if_risky": 4.0, "review": 0.25, "deny_if_benign": 1.5},
        }
    )
    assert rule.cost == Cost(allow_if_risky=4.0, review=0.25, deny_if_benign=1.5)


def test_cost_requires_positive_allow_and_deny_costs() -> None:
    with pytest.raises(ValidationError):
        Cost.model_validate({"allow_if_risky": 0.0, "review": 0.1, "deny_if_benign": 1.0})
    with pytest.raises(ValidationError):
        Cost.model_validate({"allow_if_risky": 1.0, "review": 0.1, "deny_if_benign": 0.0})


def test_default_cost_for_dimension_follows_severity_table() -> None:
    for dimension in CRITICAL_COST_DIMENSIONS:
        assert default_cost_for_dimension(dimension) == Cost(
            allow_if_risky=10.0, review=0.5, deny_if_benign=2.0
        )
    for dimension in HIGH_COST_DIMENSIONS:
        assert default_cost_for_dimension(dimension) == Cost(
            allow_if_risky=5.0, review=0.3, deny_if_benign=1.5
        )
    assert default_cost_for_dimension(RiskDimension.INSUFFICIENT_CONTEXT) == Cost(
        allow_if_risky=1.0, review=0.1, deny_if_benign=1.0
    )
    assert default_cost_for_dimension(RiskDimension.PROMPT_INJECTION_INFLUENCE) == Cost(
        allow_if_risky=3.0, review=0.2, deny_if_benign=1.0
    )
