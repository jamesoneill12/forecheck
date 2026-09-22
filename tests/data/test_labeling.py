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

    def test_forbid_bulk_above_n_violated(self) -> None:
        latent = make_latent(record_count=500)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_BULK_ABOVE_N, max_record_count=100
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_bulk_above_n_not_violated(self) -> None:
        latent = make_latent(record_count=10)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_BULK_ABOVE_N, max_record_count=100
        )
        assert evaluate_predicate(pred, latent) is False

    def test_require_ticket_reference_violated(self) -> None:
        latent = make_latent(ticket_reference=None)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_TICKET_REFERENCE)
        assert evaluate_predicate(pred, latent) is True

    def test_require_ticket_reference_not_violated(self) -> None:
        latent = make_latent(ticket_reference="TICKET-1234")
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_TICKET_REFERENCE)
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_outside_business_hours_violated(self) -> None:
        latent = make_latent(local_hour=3)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_OUTSIDE_BUSINESS_HOURS,
            business_hour_start=9,
            business_hour_end=17,
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_outside_business_hours_not_violated(self) -> None:
        latent = make_latent(local_hour=10)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_OUTSIDE_BUSINESS_HOURS,
            business_hour_start=9,
            business_hour_end=17,
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_recipient_domain_violated(self) -> None:
        latent = make_latent(recipient_domain="unknown-domain.example")
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_RECIPIENT_DOMAIN,
            allowed_domains=["corp-internal.example"],
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_recipient_domain_not_violated(self) -> None:
        latent = make_latent(recipient_domain="corp-internal.example")
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_RECIPIENT_DOMAIN,
            allowed_domains=["corp-internal.example"],
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_recipient_domain_absent_is_not_violated(self) -> None:
        latent = make_latent(recipient_domain=None)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_RECIPIENT_DOMAIN,
            allowed_domains=["corp-internal.example"],
        )
        assert evaluate_predicate(pred, latent) is False

    def test_require_dry_run_first_violated(self) -> None:
        latent = make_latent(operation=OperationKind.DELETE, dry_run_performed=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_DRY_RUN_FIRST)
        assert evaluate_predicate(pred, latent) is True

    def test_require_dry_run_first_not_violated_when_performed(self) -> None:
        latent = make_latent(operation=OperationKind.DELETE, dry_run_performed=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_DRY_RUN_FIRST)
        assert evaluate_predicate(pred, latent) is False

    def test_require_dry_run_first_not_violated_when_not_destructive(self) -> None:
        latent = make_latent(operation=OperationKind.READ, dry_run_performed=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_DRY_RUN_FIRST)
        assert evaluate_predicate(pred, latent) is False

    def test_data_residency_region_violated(self) -> None:
        latent = make_latent(resource_region="eu-west-1")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.DATA_RESIDENCY_REGION, allowed_regions=["us-east-1"]
        )
        assert evaluate_predicate(pred, latent) is True

    def test_data_residency_region_not_violated(self) -> None:
        latent = make_latent(resource_region="us-east-1")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.DATA_RESIDENCY_REGION, allowed_regions=["us-east-1"]
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_pii_field_export_violated(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            touched_pii_fields=["ssn", "email"],
        )
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_PII_FIELD_EXPORT, pii_fields=["ssn"]
        )
        assert evaluate_predicate(pred, latent) is True

    def test_forbid_pii_field_export_not_violated_without_overlap(self) -> None:
        latent = make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            touched_pii_fields=["phone"],
        )
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_PII_FIELD_EXPORT, pii_fields=["ssn"]
        )
        assert evaluate_predicate(pred, latent) is False

    def test_forbid_pii_field_export_not_violated_without_destination(self) -> None:
        latent = make_latent(destination_present=False, touched_pii_fields=["ssn"])
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_PII_FIELD_EXPORT, pii_fields=["ssn"]
        )
        assert evaluate_predicate(pred, latent) is False

    def test_every_kind_is_handled_explicitly(self) -> None:
        latent = make_latent()
        for kind in PolicyPredicateKind:
            pred = PolicyPredicate(id="p", kind=kind)
            evaluate_predicate(pred, latent)


class TestRequireManagerApprovalAboveAmount:
    def test_violated_above_threshold_without_approval(self) -> None:
        latent = make_latent(financial_amount=500.0, manager_approved=False)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_MANAGER_APPROVAL_ABOVE_AMOUNT, max_amount=100.0
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_approved(self) -> None:
        latent = make_latent(financial_amount=500.0, manager_approved=True)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_MANAGER_APPROVAL_ABOVE_AMOUNT, max_amount=100.0
        )
        assert evaluate_predicate(pred, latent) is False

    def test_not_violated_below_threshold(self) -> None:
        latent = make_latent(financial_amount=50.0, manager_approved=False)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_MANAGER_APPROVAL_ABOVE_AMOUNT, max_amount=100.0
        )
        assert evaluate_predicate(pred, latent) is False


class TestForbidCurrency:
    def test_violated_when_currency_forbidden(self) -> None:
        latent = make_latent(financial_amount=10.0, financial_currency="EUR")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_CURRENCY, forbidden_currencies=["EUR"]
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_currency_allowed(self) -> None:
        latent = make_latent(financial_amount=10.0, financial_currency="USD")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_CURRENCY, forbidden_currencies=["EUR"]
        )
        assert evaluate_predicate(pred, latent) is False

    def test_not_violated_when_no_amount(self) -> None:
        latent = make_latent(financial_amount=0.0, financial_currency="EUR")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_CURRENCY, forbidden_currencies=["EUR"]
        )
        assert evaluate_predicate(pred, latent) is False


class TestRequireTwoPersonRuleForDestructive:
    def test_violated_when_destructive_without_second_approver(self) -> None:
        latent = make_latent(operation=OperationKind.DELETE, second_approver_present=False)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_TWO_PERSON_RULE_FOR_DESTRUCTIVE
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_second_approver_present(self) -> None:
        latent = make_latent(operation=OperationKind.DELETE, second_approver_present=True)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_TWO_PERSON_RULE_FOR_DESTRUCTIVE
        )
        assert evaluate_predicate(pred, latent) is False

    def test_not_violated_when_not_destructive(self) -> None:
        latent = make_latent(operation=OperationKind.READ, second_approver_present=False)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.REQUIRE_TWO_PERSON_RULE_FOR_DESTRUCTIVE
        )
        assert evaluate_predicate(pred, latent) is False


class TestForbidToolFamilyForRole:
    def test_violated_when_role_and_family_match(self) -> None:
        latent = make_latent(principal_roles=["contractor"])
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_TOOL_FAMILY_FOR_ROLE,
            role="contractor",
            forbidden_tool_family=latent.tool.family,
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_role_does_not_match(self) -> None:
        latent = make_latent(principal_roles=["employee"])
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.FORBID_TOOL_FAMILY_FOR_ROLE,
            role="contractor",
            forbidden_tool_family=latent.tool.family,
        )
        assert evaluate_predicate(pred, latent) is False


class TestRequireCustomerConsentFlag:
    def test_violated_without_consent(self) -> None:
        latent = make_latent(customer_consent_given=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_CUSTOMER_CONSENT_FLAG)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_with_consent(self) -> None:
        latent = make_latent(customer_consent_given=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_CUSTOMER_CONSENT_FLAG)
        assert evaluate_predicate(pred, latent) is False


class TestForbidExportFormat:
    def test_violated_when_format_forbidden(self) -> None:
        latent = make_latent(export_format="csv")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_EXPORT_FORMAT, forbidden_export_formats=["csv"]
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_without_export_format(self) -> None:
        latent = make_latent(export_format=None)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_EXPORT_FORMAT, forbidden_export_formats=["csv"]
        )
        assert evaluate_predicate(pred, latent) is False


class TestForbidChannel:
    def test_violated_when_channel_forbidden(self) -> None:
        latent = make_latent(channel="sms")
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_CHANNEL, forbidden_channels=["sms"]
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_without_channel(self) -> None:
        latent = make_latent(channel=None)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_CHANNEL, forbidden_channels=["sms"]
        )
        assert evaluate_predicate(pred, latent) is False


class TestRequireEncryptionInTransitFlag:
    def test_violated_when_destination_present_without_encryption(self) -> None:
        latent = make_latent(destination_present=True, encryption_in_transit=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_ENCRYPTION_IN_TRANSIT_FLAG)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_no_destination(self) -> None:
        latent = make_latent(destination_present=False, encryption_in_transit=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_ENCRYPTION_IN_TRANSIT_FLAG)
        assert evaluate_predicate(pred, latent) is False


class TestRequireReasonFieldNonempty:
    def test_violated_when_reason_empty(self) -> None:
        latent = make_latent(reason="")
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_REASON_FIELD_NONEMPTY)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_reason_given(self) -> None:
        latent = make_latent(reason="customer requested account review")
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_REASON_FIELD_NONEMPTY)
        assert evaluate_predicate(pred, latent) is False


class TestForbidWeekendOps:
    def test_violated_on_weekend(self) -> None:
        latent = make_latent(is_weekend=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_WEEKEND_OPS)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_on_weekday(self) -> None:
        latent = make_latent(is_weekend=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_WEEKEND_OPS)
        assert evaluate_predicate(pred, latent) is False


class TestRequireRecipientVerifiedFlag:
    def test_violated_when_destination_unverified(self) -> None:
        latent = make_latent(destination_present=True, recipient_verified=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_RECIPIENT_VERIFIED_FLAG)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_verified(self) -> None:
        latent = make_latent(destination_present=True, recipient_verified=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_RECIPIENT_VERIFIED_FLAG)
        assert evaluate_predicate(pred, latent) is False

    def test_not_violated_without_destination(self) -> None:
        latent = make_latent(destination_present=False, recipient_verified=None)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_RECIPIENT_VERIFIED_FLAG)
        assert evaluate_predicate(pred, latent) is False


class TestRequireDataClassificationBelow:
    def test_violated_above_ceiling(self) -> None:
        latent = make_latent(resource_sensitivity=Sensitivity.RESTRICTED)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.REQUIRE_DATA_CLASSIFICATION_BELOW,
            max_allowed_sensitivity=Sensitivity.CONFIDENTIAL,
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_at_or_below_ceiling(self) -> None:
        latent = make_latent(resource_sensitivity=Sensitivity.CONFIDENTIAL)
        pred = PolicyPredicate(
            id="p",
            kind=PolicyPredicateKind.REQUIRE_DATA_CLASSIFICATION_BELOW,
            max_allowed_sensitivity=Sensitivity.CONFIDENTIAL,
        )
        assert evaluate_predicate(pred, latent) is False


class TestForbidActionAfterFailedAuthInTrajectory:
    def test_violated_when_failed_auth_present(self) -> None:
        latent = make_latent(failed_auth_in_trajectory=True)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_ACTION_AFTER_FAILED_AUTH_IN_TRAJECTORY
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_without_failed_auth(self) -> None:
        latent = make_latent(failed_auth_in_trajectory=False)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_ACTION_AFTER_FAILED_AUTH_IN_TRAJECTORY
        )
        assert evaluate_predicate(pred, latent) is False


class TestMaxRecordsPerDayQuota:
    def test_violated_above_daily_quota(self) -> None:
        latent = make_latent(records_processed_today=900, record_count=200)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.MAX_RECORDS_PER_DAY_QUOTA, max_daily_record_count=1000
        )
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_within_daily_quota(self) -> None:
        latent = make_latent(records_processed_today=100, record_count=50)
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.MAX_RECORDS_PER_DAY_QUOTA, max_daily_record_count=1000
        )
        assert evaluate_predicate(pred, latent) is False


class TestForbidCrossTenantReference:
    def test_violated_when_cross_tenant(self) -> None:
        latent = make_latent(cross_tenant_resource=True)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_CROSS_TENANT_REFERENCE)
        assert evaluate_predicate(pred, latent) is True

    def test_not_violated_when_same_tenant(self) -> None:
        latent = make_latent(cross_tenant_resource=False)
        pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_CROSS_TENANT_REFERENCE)
        assert evaluate_predicate(pred, latent) is False
