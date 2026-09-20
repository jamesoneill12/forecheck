"""Every rule in every shipped bundle fires under at least one constructed input.

This is a dead-rule detector: a rule whose condition can never be satisfied (a typo'd
threshold, a fact check that contradicts another rule's, ...) fails here even though it
never fails DSL validation.
"""

from __future__ import annotations

from forecheck.contracts import (
    AffectedResource,
    AgentIdentity,
    Destination,
    DestinationRelationship,
    Environment,
    FinancialExposure,
    OperationKind,
    Principal,
    PrincipalType,
    ResourceKind,
    RiskDimension,
    Sensitivity,
    Stage,
    TrustLevel,
    UserObjective,
)
from forecheck.policies.builtin import load_builtin_engine

from .conftest import benign_classification, benign_context

RD = RiskDimension

_MUTATING_RESOURCE = [
    AffectedResource(
        urn="urn:file:target",
        kind=ResourceKind.FILE,
        sensitivity=Sensitivity.PUBLIC,
        operation=OperationKind.UPDATE,
        reversible=False,
    )
]

_UNAUTHORIZED_OBJECTIVE = UserObjective(text="Do the thing.", authorization_explicit=False)


def _confidential_exfil_context(
    sensitivity: Sensitivity = Sensitivity.CONFIDENTIAL,
) -> dict[str, object]:
    return {
        "resources": [
            AffectedResource(
                urn="urn:table:customers",
                kind=ResourceKind.TABLE,
                sensitivity=sensitivity,
                operation=OperationKind.READ,
                reversible=True,
            )
        ],
        "destination": Destination(
            identifier="unknown@external.example",
            relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            trust=TrustLevel.UNKNOWN,
        ),
    }


def _production_freeze_context() -> dict[str, object]:
    return {"environment": Environment(stage=Stage.PRODUCTION, change_freeze=True)}


def _no_delegated_scope_context() -> dict[str, object]:
    return {"agent": AgentIdentity(id="agent-1", delegated_scopes=[])}


def _financial_context(amount: float) -> dict[str, object]:
    return {
        "financial": FinancialExposure(amount=amount),
        "objective": _UNAUTHORIZED_OBJECTIVE,
    }


def _restricted_no_mfa_context() -> dict[str, object]:
    return {
        "resources": [
            AffectedResource(
                urn="urn:secret:vault-entry",
                kind=ResourceKind.CREDENTIAL,
                sensitivity=Sensitivity.RESTRICTED,
                operation=OperationKind.READ,
                reversible=True,
            )
        ],
        "principal": Principal(id="user-1", type=PrincipalType.HUMAN, mfa_satisfied=False),
    }


CONSERVATIVE_CASES: list[tuple[str, dict[RiskDimension, float], dict[str, object]]] = [
    (
        "injection_drives_mutation",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9},
        {"resources": _MUTATING_RESOURCE},
    ),
    (
        "injection_drives_external_communication",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9, RD.EXTERNAL_COMMUNICATION: 0.9},
        {},
    ),
    (
        "exfiltration_confidential_to_untrusted_destination",
        {RD.SENSITIVE_DATA_EXPOSURE: 0.9},
        _confidential_exfil_context(),
    ),
    (
        "privilege_escalation_without_authorization",
        {RD.PRIVILEGE_ESCALATION: 0.9},
        {"objective": _UNAUTHORIZED_OBJECTIVE},
    ),
    (
        "destructive_production_change_freeze",
        {RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.9},
        _production_freeze_context(),
    ),
    (
        "unauthorized_scope_and_no_delegated_scope",
        {RD.UNAUTHORIZED_SCOPE: 0.9},
        _no_delegated_scope_context(),
    ),
    ("financial_commitment_unauthorized", {RD.FINANCIAL_COMMITMENT: 0.9}, _financial_context(500)),
    ("attack_shaped_sequence", {RD.SUSPICIOUS_ACTION_SEQUENCE: 0.9}, {}),
    ("review_injection_present", {RD.PROMPT_INJECTION_INFLUENCE: 0.3}, {}),
    ("review_sensitive_exposure", {RD.SENSITIVE_DATA_EXPOSURE: 0.3}, {}),
    ("review_untrusted_destination", {RD.UNTRUSTED_DESTINATION: 0.4}, {}),
    ("review_privilege_escalation_present", {RD.PRIVILEGE_ESCALATION: 0.3}, {}),
    ("review_destructive_action_present", {RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.3}, {}),
    ("review_financial_commitment_present", {RD.FINANCIAL_COMMITMENT: 0.2}, {}),
    ("review_policy_conflict", {RD.POLICY_CONFLICT: 0.4}, {}),
    ("review_insufficient_context", {RD.INSUFFICIENT_CONTEXT: 0.6}, {}),
    (
        "review_missing_mfa_for_sensitive_resource",
        {},
        _restricted_no_mfa_context(),
    ),
    ("allow_authorized_reversible_dev_action", {}, {}),
]

BALANCED_CASES: list[tuple[str, dict[RiskDimension, float], dict[str, object]]] = [
    (
        "injection_drives_mutation",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9},
        {"resources": _MUTATING_RESOURCE},
    ),
    (
        "injection_drives_external_communication",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9, RD.EXTERNAL_COMMUNICATION: 0.9},
        {},
    ),
    (
        "exfiltration_confidential_to_untrusted_destination",
        {RD.SENSITIVE_DATA_EXPOSURE: 0.9},
        _confidential_exfil_context(),
    ),
    (
        "privilege_escalation_without_authorization",
        {RD.PRIVILEGE_ESCALATION: 0.9},
        {"objective": _UNAUTHORIZED_OBJECTIVE},
    ),
    (
        "destructive_production_change_freeze",
        {RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.9},
        _production_freeze_context(),
    ),
    (
        "unauthorized_scope_and_no_delegated_scope",
        {RD.UNAUTHORIZED_SCOPE: 0.9},
        _no_delegated_scope_context(),
    ),
    ("financial_commitment_unauthorized", {RD.FINANCIAL_COMMITMENT: 0.9}, _financial_context(2000)),
    ("attack_shaped_sequence", {RD.SUSPICIOUS_ACTION_SEQUENCE: 0.9}, {}),
    ("review_injection_medium", {RD.PROMPT_INJECTION_INFLUENCE: 0.4}, {}),
    ("review_sensitive_exposure_medium", {RD.SENSITIVE_DATA_EXPOSURE: 0.45}, {}),
    ("review_untrusted_destination_medium", {RD.UNTRUSTED_DESTINATION: 0.5}, {}),
    ("review_privilege_escalation_medium", {RD.PRIVILEGE_ESCALATION: 0.4}, {}),
    ("review_destructive_action_medium", {RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.45}, {}),
    ("review_financial_commitment_medium", {RD.FINANCIAL_COMMITMENT: 0.4}, {}),
    ("review_policy_conflict", {RD.POLICY_CONFLICT: 0.55}, {}),
    ("review_insufficient_context", {RD.INSUFFICIENT_CONTEXT: 0.65}, {}),
    (
        "review_missing_mfa_for_sensitive_resource",
        {},
        _restricted_no_mfa_context(),
    ),
    ("allow_reversible_dev_action", {}, {}),
]

PERMISSIVE_CASES: list[tuple[str, dict[RiskDimension, float], dict[str, object]]] = [
    (
        "injection_drives_irreversible_action",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9, RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.9},
        {},
    ),
    (
        "injection_drives_financial_action",
        {RD.PROMPT_INJECTION_INFLUENCE: 0.9, RD.FINANCIAL_COMMITMENT: 0.9},
        {},
    ),
    (
        "exfiltration_of_secret_data",
        {RD.SENSITIVE_DATA_EXPOSURE: 0.9},
        _confidential_exfil_context(Sensitivity.SECRET),
    ),
    (
        "privilege_escalation_unambiguous",
        {RD.PRIVILEGE_ESCALATION: 0.9},
        {"objective": _UNAUTHORIZED_OBJECTIVE},
    ),
    ("review_injection_high", {RD.PROMPT_INJECTION_INFLUENCE: 0.65}, {}),
    ("review_sensitive_exposure_high", {RD.SENSITIVE_DATA_EXPOSURE: 0.65}, {}),
    ("review_privilege_escalation_high", {RD.PRIVILEGE_ESCALATION: 0.6}, {}),
    ("review_destructive_action_high", {RD.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.72}, {}),
    ("review_financial_commitment_high", {RD.FINANCIAL_COMMITMENT: 0.72}, {}),
    ("review_attack_shaped_sequence", {RD.SUSPICIOUS_ACTION_SEQUENCE: 0.85}, {}),
    ("review_insufficient_context", {RD.INSUFFICIENT_CONTEXT: 0.75}, {}),
    ("allow_development_stage_action", {}, {}),
]

_ALL_CASES = {
    "conservative": CONSERVATIVE_CASES,
    "balanced": BALANCED_CASES,
    "permissive": PERMISSIVE_CASES,
}


def _fired_rule_ids(
    bundle_name: str,
    rule_id: str,
    scores: dict[RiskDimension, float],
    context_overrides: dict[str, object],
) -> set[str]:
    engine = load_builtin_engine(bundle_name)
    classification = benign_classification(scores)
    context = benign_context(**context_overrides)
    decision = engine.evaluate(classification, context=context)
    return {match.rule_id for match in decision.matched_rules}


def test_conservative_case_ids_cover_every_rule() -> None:
    engine = load_builtin_engine("conservative")
    covered = {case[0] for case in CONSERVATIVE_CASES}
    assert covered == {rule.id for rule in engine.bundle.rules}


def test_balanced_case_ids_cover_every_rule() -> None:
    engine = load_builtin_engine("balanced")
    covered = {case[0] for case in BALANCED_CASES}
    assert covered == {rule.id for rule in engine.bundle.rules}


def test_permissive_case_ids_cover_every_rule() -> None:
    engine = load_builtin_engine("permissive")
    covered = {case[0] for case in PERMISSIVE_CASES}
    assert covered == {rule.id for rule in engine.bundle.rules}


def test_every_conservative_rule_fires() -> None:
    for rule_id, scores, context_overrides in CONSERVATIVE_CASES:
        fired = _fired_rule_ids("conservative", rule_id, scores, context_overrides)
        assert rule_id in fired, f"{rule_id} never fired: {fired}"


def test_every_balanced_rule_fires() -> None:
    for rule_id, scores, context_overrides in BALANCED_CASES:
        fired = _fired_rule_ids("balanced", rule_id, scores, context_overrides)
        assert rule_id in fired, f"{rule_id} never fired: {fired}"


def test_every_permissive_rule_fires() -> None:
    for rule_id, scores, context_overrides in PERMISSIVE_CASES:
        fired = _fired_rule_ids("permissive", rule_id, scores, context_overrides)
        assert rule_id in fired, f"{rule_id} never fired: {fired}"
