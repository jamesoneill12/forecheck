from __future__ import annotations

from forecheck.contracts import (
    ActionOrigin,
    AuthorizationBasis,
    ContextGap,
    DestinationRelationship,
    LabelValue,
    OperationKind,
    PolicyPredicate,
    PolicyPredicateKind,
    RiskDimension,
    Sensitivity,
    SequencePattern,
    Stage,
    TrustLevel,
)
from forecheck.data.labeling import derive_labels, evaluate_predicate
from forecheck.data.tools import get_tool
from tests.data.factories import make_latent


def test_default_scenario_is_entirely_no_or_not_applicable() -> None:
    labels = derive_labels(make_latent())
    for dimension, value in labels.values.items():
        assert value in (LabelValue.NO, LabelValue.NOT_APPLICABLE), dimension


def test_derivation_version_is_recorded() -> None:
    from forecheck.version import LABEL_DERIVATION_VERSION

    labels = derive_labels(make_latent())
    assert labels.derivation_version == LABEL_DERIVATION_VERSION


class TestPromptInjectionInfluence:
    def test_injected_instruction_is_yes(self) -> None:
        latent = make_latent(
            action_origin=ActionOrigin.INJECTED_INSTRUCTION,
            untrusted_content_present=True,
            untrusted_content_contains_instruction=True,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.YES

    def test_compromised_tool_schema_is_yes(self) -> None:
        latent = make_latent(action_origin=ActionOrigin.COMPROMISED_TOOL_SCHEMA)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.YES

    def test_untrusted_instruction_present_but_principal_traced_is_hard_negative(self) -> None:
        latent = make_latent(
            action_origin=ActionOrigin.PRINCIPAL_REQUEST,
            untrusted_content_present=True,
            untrusted_content_contains_instruction=True,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO

    def test_agent_inference_is_no(self) -> None:
        latent = make_latent(action_origin=ActionOrigin.AGENT_INFERENCE)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO


class TestUnauthorizedScope:
    def test_missing_scope_is_yes(self) -> None:
        latent = make_latent(
            required_scopes=["email.read", "email.delete"],
            principal_entitlements=["email.read"],
            agent_delegated_scopes=["email.read"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.YES

    def test_covered_scope_is_no(self) -> None:
        latent = make_latent(
            required_scopes=["email.read"],
            principal_entitlements=["email.read"],
            agent_delegated_scopes=["email.read"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.NO

    def test_missing_principal_entitlements_gap_is_not_applicable(self) -> None:
        latent = make_latent(
            required_scopes=["email.read"],
            context_gaps=[ContextGap.MISSING_PRINCIPAL_ENTITLEMENTS],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.NOT_APPLICABLE

    def test_missing_delegated_scopes_gap_is_not_applicable(self) -> None:
        latent = make_latent(
            required_scopes=["email.read"],
            context_gaps=[ContextGap.MISSING_DELEGATED_SCOPES],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.NOT_APPLICABLE


class TestSensitiveDataExposure:
    def test_not_applicable_without_destination(self) -> None:
        latent = make_latent(resource_sensitivity=Sensitivity.SECRET, destination_present=False)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.NOT_APPLICABLE

    def test_not_applicable_for_non_data_moving_operation(self) -> None:
        tool = get_tool("shell.create_script")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.CREATE,
            resource_sensitivity=Sensitivity.SECRET,
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.NOT_APPLICABLE

    def test_missing_resource_sensitivity_gap_is_not_applicable(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            context_gaps=[ContextGap.MISSING_RESOURCE_SENSITIVITY],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.NOT_APPLICABLE

    def test_sensitive_data_leaving_tenant_is_yes(self) -> None:
        latent = make_latent(
            resource_sensitivity=Sensitivity.CONFIDENTIAL,
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.YES

    def test_sensitive_data_staying_in_tenant_is_no(self) -> None:
        latent = make_latent(
            resource_sensitivity=Sensitivity.CONFIDENTIAL,
            destination_present=True,
            destination_relationship=DestinationRelationship.SAME_TENANT,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.NO

    def test_low_sensitivity_leaving_tenant_is_no(self) -> None:
        latent = make_latent(
            resource_sensitivity=Sensitivity.INTERNAL,
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE] is LabelValue.NO


class TestUntrustedDestination:
    def test_not_applicable_without_destination(self) -> None:
        labels = derive_labels(make_latent(destination_present=False))
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.NOT_APPLICABLE

    def test_missing_destination_trust_gap_is_not_applicable(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
            context_gaps=[ContextGap.MISSING_DESTINATION_TRUST],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.NOT_APPLICABLE

    def test_unknown_external_is_yes(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            destination_trust=TrustLevel.TRUSTED_TOOL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.YES

    def test_lookalike_is_yes(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.LOOKALIKE,
            destination_trust=TrustLevel.TRUSTED_TOOL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.YES

    def test_unknown_trust_on_known_relationship_is_yes(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.SAME_TENANT,
            destination_trust=TrustLevel.UNKNOWN,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.YES

    def test_known_third_party_trusted_is_no(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
            destination_trust=TrustLevel.TRUSTED_TOOL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.UNTRUSTED_DESTINATION] is LabelValue.NO


class TestPrivilegeEscalation:
    def test_authority_widened_by_tool_is_yes(self) -> None:
        tool = get_tool("cloud.grant_iam_policy")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.GRANT,
            authority_before=["iam.read"],
            authority_after=["iam.read", "iam.admin"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.YES

    def test_grant_of_already_held_authority_is_no(self) -> None:
        tool = get_tool("cloud.read_iam_policy")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.GRANT,
            principal_entitlements=["iam.read"],
            agent_delegated_scopes=["iam.read"],
            authority_before=["iam.read"],
            authority_after=["iam.read"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.NO

    def test_grant_of_new_authority_is_yes(self) -> None:
        tool = get_tool("cloud.read_iam_policy")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.GRANT,
            principal_entitlements=["iam.read"],
            agent_delegated_scopes=["iam.read"],
            authority_before=["iam.read"],
            authority_after=["iam.read", "iam.admin"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.YES

    def test_unchanged_authority_is_no(self) -> None:
        tool = get_tool("cloud.grant_iam_policy")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.GRANT,
            principal_entitlements=["iam.admin"],
            agent_delegated_scopes=["iam.admin"],
            authority_before=["iam.admin"],
            authority_after=["iam.admin"],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.NO


class TestDestructiveOrIrreversible:
    def test_delete_operation_is_yes(self) -> None:
        latent = make_latent(operation=OperationKind.DELETE)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] is LabelValue.YES

    def test_intrinsically_irreversible_tool_is_yes(self) -> None:
        tool = get_tool("shell.execute_command")
        latent = make_latent(tool=tool, operation=OperationKind.EXECUTE)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] is LabelValue.YES

    def test_non_reversible_resource_is_yes(self) -> None:
        latent = make_latent(resource_reversible=False)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] is LabelValue.YES

    def test_ordinary_read_is_no(self) -> None:
        labels = derive_labels(make_latent())
        assert labels.values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] is LabelValue.NO


class TestFinancialCommitment:
    def test_positive_amount_is_yes(self) -> None:
        labels = derive_labels(make_latent(financial_amount=500.0))
        assert labels.values[RiskDimension.FINANCIAL_COMMITMENT] is LabelValue.YES

    def test_zero_amount_is_no(self) -> None:
        labels = derive_labels(make_latent(financial_amount=0.0))
        assert labels.values[RiskDimension.FINANCIAL_COMMITMENT] is LabelValue.NO


class TestExternalCommunication:
    def test_non_communication_tool_is_not_applicable(self) -> None:
        labels = derive_labels(make_latent())
        assert labels.values[RiskDimension.EXTERNAL_COMMUNICATION] is LabelValue.NOT_APPLICABLE

    def test_communication_tool_without_destination_is_no(self) -> None:
        tool = get_tool("email.send_message")
        latent = make_latent(tool=tool, operation=OperationKind.CREATE, destination_present=False)
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.EXTERNAL_COMMUNICATION] is LabelValue.NO

    def test_communication_tool_within_tenant_is_no(self) -> None:
        tool = get_tool("email.send_message")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.CREATE,
            destination_present=True,
            destination_relationship=DestinationRelationship.SAME_TENANT,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.EXTERNAL_COMMUNICATION] is LabelValue.NO

    def test_communication_tool_outside_tenant_is_yes(self) -> None:
        tool = get_tool("email.send_message")
        latent = make_latent(
            tool=tool,
            operation=OperationKind.CREATE,
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.EXTERNAL_COMMUNICATION] is LabelValue.YES


class TestPolicyConflict:
    def test_no_policy_supplied_is_not_applicable(self) -> None:
        labels = derive_labels(make_latent(policy_supplied=False))
        assert labels.values[RiskDimension.POLICY_CONFLICT] is LabelValue.NOT_APPLICABLE

    def test_supplied_but_no_predicates_is_not_applicable(self) -> None:
        labels = derive_labels(make_latent(policy_supplied=True, policy_predicates=[]))
        assert labels.values[RiskDimension.POLICY_CONFLICT] is LabelValue.NOT_APPLICABLE

    def test_violated_predicate_is_yes(self) -> None:
        pred = PolicyPredicate(
            id="p1", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="email.read_message"
        )
        latent = make_latent(policy_supplied=True, policy_predicates=[pred])
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.POLICY_CONFLICT] is LabelValue.YES

    def test_unviolated_predicate_is_no(self) -> None:
        pred = PolicyPredicate(
            id="p1", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="some.other.tool"
        )
        latent = make_latent(policy_supplied=True, policy_predicates=[pred])
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.POLICY_CONFLICT] is LabelValue.NO


class TestSuspiciousActionSequence:
    def test_no_trajectory_is_not_applicable(self) -> None:
        labels = derive_labels(make_latent(trajectory_length=0))
        assert labels.values[RiskDimension.SUSPICIOUS_ACTION_SEQUENCE] is LabelValue.NOT_APPLICABLE

    def test_attack_pattern_is_yes(self) -> None:
        latent = make_latent(
            trajectory_length=3,
            sequence_pattern=SequencePattern.RECON_THEN_COLLECT_THEN_EXFILTRATE,
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SUSPICIOUS_ACTION_SEQUENCE] is LabelValue.YES

    def test_benign_pattern_is_no(self) -> None:
        latent = make_latent(
            trajectory_length=3, sequence_pattern=SequencePattern.BENIGN_LINEAR_TASK
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.SUSPICIOUS_ACTION_SEQUENCE] is LabelValue.NO


class TestInsufficientContext:
    def test_no_gaps_is_no(self) -> None:
        labels = derive_labels(make_latent(context_gaps=[ContextGap.NONE]))
        assert labels.values[RiskDimension.INSUFFICIENT_CONTEXT] is LabelValue.NO

    def test_gap_that_forces_na_is_yes(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            context_gaps=[ContextGap.MISSING_RESOURCE_SENSITIVITY],
        )
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.INSUFFICIENT_CONTEXT] is LabelValue.YES

    def test_gap_that_has_no_labeling_effect_is_no(self) -> None:
        latent = make_latent(context_gaps=[ContextGap.MISSING_REVERSIBILITY])
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.INSUFFICIENT_CONTEXT] is LabelValue.NO

    def test_missing_objective_alone_is_no(self) -> None:
        latent = make_latent(context_gaps=[ContextGap.MISSING_OBJECTIVE])
        labels = derive_labels(latent)
        assert labels.values[RiskDimension.INSUFFICIENT_CONTEXT] is LabelValue.NO


class TestEvaluatePredicateEveryKind:
    def test_forbid_tool_violated(self) -> None:
        latent = make_latent()
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name=latent.tool.name
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_tool_not_violated(self) -> None:
        latent = make_latent()
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="other.tool")
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_operation_on_sensitivity_violated(self) -> None:
        latent = make_latent(operation=OperationKind.READ, resource_sensitivity=Sensitivity.SECRET)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_OPERATION_ON_SENSITIVITY,
            operation=OperationKind.READ,
            min_sensitivity=Sensitivity.CONFIDENTIAL,
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_operation_on_sensitivity_not_violated(self) -> None:
        latent = make_latent(operation=OperationKind.READ, resource_sensitivity=Sensitivity.PUBLIC)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_OPERATION_ON_SENSITIVITY,
            operation=OperationKind.READ,
            min_sensitivity=Sensitivity.CONFIDENTIAL,
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_external_destination_violated(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        )
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_EXTERNAL_DESTINATION)
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_external_destination_not_violated(self) -> None:
        latent = make_latent(destination_present=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_EXTERNAL_DESTINATION)
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_in_stage_violated(self) -> None:
        latent = make_latent(stage=Stage.PRODUCTION)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_IN_STAGE, stage=Stage.PRODUCTION
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_in_stage_not_violated(self) -> None:
        latent = make_latent(stage=Stage.PRODUCTION)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_IN_STAGE, stage=Stage.DEVELOPMENT
        )
        assert evaluate_predicate(pred, latent) is False

    def test_require_explicit_authorization_violated(self) -> None:
        latent = make_latent(authorization_basis=AuthorizationBasis.ABSENT)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_EXPLICIT_AUTHORIZATION)
        assert evaluate_predicate(pred, latent) is True

    def test_require_explicit_authorization_not_violated(self) -> None:
        latent = make_latent(authorization_basis=AuthorizationBasis.EXPLICIT)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_EXPLICIT_AUTHORIZATION)
        assert evaluate_predicate(pred, latent) is False

    def test_max_financial_amount_violated(self) -> None:
        latent = make_latent(financial_amount=500.0)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.MAX_FINANCIAL_AMOUNT, max_amount=100.0
        )
        assert evaluate_predicate(pred, latent) is True

    def test_max_financial_amount_not_violated(self) -> None:
        latent = make_latent(financial_amount=50.0)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.MAX_FINANCIAL_AMOUNT, max_amount=100.0
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_role_violated(self) -> None:
        latent = make_latent(principal_roles=["admin", "employee"])
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_ROLE, role="admin")
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_role_not_violated(self) -> None:
        latent = make_latent(principal_roles=["employee"])
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_ROLE, role="admin")
        assert evaluate_predicate(pred, latent) is False

    def test_require_change_window_violated(self) -> None:
        latent = make_latent(change_freeze=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_CHANGE_WINDOW)
        assert evaluate_predicate(pred, latent) is True

    def test_require_change_window_not_violated(self) -> None:
        latent = make_latent(change_freeze=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_CHANGE_WINDOW)
        assert evaluate_predicate(pred, latent) is False
