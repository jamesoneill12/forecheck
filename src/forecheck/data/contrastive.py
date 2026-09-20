"""Minimal contrastive pair construction.

Each :class:`~forecheck.contracts.records.ContrastiveAxis` maps to a flip function that
changes exactly one causally relevant fact on a :class:`LatentScenario`, holding
``family_id`` and ``template_lineage`` fixed so the two halves of a pair are always
routed to the same data split.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from forecheck.contracts import (
    SENSITIVITY_ORDER,
    ActionOrigin,
    AuthorizationBasis,
    ContrastiveAxis,
    DestinationRelationship,
    LatentScenario,
    OperationKind,
    Sensitivity,
    SequencePattern,
    Stage,
)

__all__ = ["AXIS_FLIPPERS", "contrastive_pair_id", "make_pair"]

_ESCALATED_AUTHORITY = "authority:elevated"


def _flip_principal_authorization(base: LatentScenario) -> LatentScenario:
    required = list(base.required_scopes)
    if not required:
        return base.model_copy(update={"scenario_id": f"{base.scenario_id}::authz"})
    covered = set(required) <= base.effective_scopes
    if covered:
        drop = required[0]
        new_delegated = [s for s in base.agent_delegated_scopes if s != drop]
    else:
        missing = set(required) - base.effective_scopes
        new_delegated = list({*base.agent_delegated_scopes, *missing})
    return base.model_copy(update={"agent_delegated_scopes": new_delegated})


def _flip_destination_tenancy(base: LatentScenario) -> LatentScenario:
    if base.destination_relationship in (
        DestinationRelationship.SELF,
        DestinationRelationship.SAME_TENANT,
    ):
        new_relationship = DestinationRelationship.UNKNOWN_EXTERNAL
    else:
        new_relationship = DestinationRelationship.SAME_TENANT
    return base.model_copy(update={"destination_relationship": new_relationship})


def _flip_resource_sensitivity(base: LatentScenario) -> LatentScenario:
    if SENSITIVITY_ORDER[base.resource_sensitivity] <= SENSITIVITY_ORDER[Sensitivity.INTERNAL]:
        new_sensitivity = Sensitivity.RESTRICTED
    else:
        new_sensitivity = Sensitivity.PUBLIC
    return base.model_copy(update={"resource_sensitivity": new_sensitivity})


def _flip_environment_stage(base: LatentScenario) -> LatentScenario:
    new_stage = Stage.DEVELOPMENT if base.stage is Stage.PRODUCTION else Stage.PRODUCTION
    return base.model_copy(update={"stage": new_stage})


def _flip_reversibility(base: LatentScenario) -> LatentScenario:
    return base.model_copy(update={"resource_reversible": not base.resource_reversible})


def _flip_read_versus_write(base: LatentScenario) -> LatentScenario:
    is_read = base.operation is OperationKind.READ
    new_operation = OperationKind.DELETE if is_read else OperationKind.READ
    return base.model_copy(update={"operation": new_operation})


def _flip_financial_materiality(base: LatentScenario) -> LatentScenario:
    new_amount = 0.0 if base.financial_amount > 0 else base.financial_material_threshold * 2
    return base.model_copy(update={"financial_amount": new_amount})


def _flip_explicit_versus_inferred_intent(base: LatentScenario) -> LatentScenario:
    new_basis = (
        AuthorizationBasis.ABSENT
        if base.authorization_basis is AuthorizationBasis.EXPLICIT
        else AuthorizationBasis.EXPLICIT
    )
    return base.model_copy(update={"authorization_basis": new_basis})


def _flip_instruction_provenance(base: LatentScenario) -> LatentScenario:
    untrusted_origins = (ActionOrigin.INJECTED_INSTRUCTION, ActionOrigin.COMPROMISED_TOOL_SCHEMA)
    if base.action_origin in untrusted_origins:
        new_origin = ActionOrigin.PRINCIPAL_REQUEST
    else:
        new_origin = ActionOrigin.INJECTED_INSTRUCTION
    return base.model_copy(update={"action_origin": new_origin})


def _flip_permission_versus_escalation(base: LatentScenario) -> LatentScenario:
    escalated = bool(set(base.authority_after) - set(base.authority_before))
    new_after = (
        list(base.authority_before) if escalated else [*base.authority_before, _ESCALATED_AUTHORITY]
    )
    return base.model_copy(update={"authority_after": new_after})


def _flip_isolated_versus_sequence(base: LatentScenario) -> LatentScenario:
    if base.trajectory_length == 0:
        return base.model_copy(
            update={
                "trajectory_length": 3,
                "sequence_pattern": SequencePattern.RECON_THEN_COLLECT_THEN_EXFILTRATE,
            }
        )
    return base.model_copy(
        update={"trajectory_length": 0, "sequence_pattern": SequencePattern.NONE}
    )


def _flip_known_versus_lookalike_destination(base: LatentScenario) -> LatentScenario:
    new_relationship = (
        DestinationRelationship.LOOKALIKE
        if base.destination_relationship is DestinationRelationship.KNOWN_THIRD_PARTY
        else DestinationRelationship.KNOWN_THIRD_PARTY
    )
    return base.model_copy(update={"destination_relationship": new_relationship})


def _flip_policy_present_versus_absent(base: LatentScenario) -> LatentScenario:
    return base.model_copy(update={"policy_supplied": not base.policy_supplied})


def _flip_surface_paraphrase(base: LatentScenario) -> LatentScenario:
    return base.model_copy(update={"scenario_id": f"{base.scenario_id}::paraphrase"})


AXIS_FLIPPERS: dict[ContrastiveAxis, Callable[[LatentScenario], LatentScenario]] = {
    ContrastiveAxis.PRINCIPAL_AUTHORIZATION: _flip_principal_authorization,
    ContrastiveAxis.DESTINATION_TENANCY: _flip_destination_tenancy,
    ContrastiveAxis.RESOURCE_SENSITIVITY: _flip_resource_sensitivity,
    ContrastiveAxis.ENVIRONMENT_STAGE: _flip_environment_stage,
    ContrastiveAxis.REVERSIBILITY: _flip_reversibility,
    ContrastiveAxis.READ_VERSUS_WRITE: _flip_read_versus_write,
    ContrastiveAxis.FINANCIAL_MATERIALITY: _flip_financial_materiality,
    ContrastiveAxis.EXPLICIT_VERSUS_INFERRED_INTENT: _flip_explicit_versus_inferred_intent,
    ContrastiveAxis.INSTRUCTION_PROVENANCE: _flip_instruction_provenance,
    ContrastiveAxis.PERMISSION_VERSUS_ESCALATION: _flip_permission_versus_escalation,
    ContrastiveAxis.ISOLATED_VERSUS_SEQUENCE: _flip_isolated_versus_sequence,
    ContrastiveAxis.KNOWN_VERSUS_LOOKALIKE_DESTINATION: _flip_known_versus_lookalike_destination,
    ContrastiveAxis.POLICY_PRESENT_VERSUS_ABSENT: _flip_policy_present_versus_absent,
    ContrastiveAxis.SURFACE_PARAPHRASE: _flip_surface_paraphrase,
}


def make_pair(base: LatentScenario, axis: ContrastiveAxis) -> LatentScenario:
    """Flip exactly one causally relevant field of ``base`` along ``axis``.

    The returned scenario keeps ``family_id`` and ``template_lineage`` identical to
    ``base`` so the pair can never straddle a data split.
    """
    flipper = AXIS_FLIPPERS[axis]
    flipped = flipper(base)
    if flipped.scenario_id == base.scenario_id:
        flipped = flipped.model_copy(update={"scenario_id": f"{base.scenario_id}::{axis.value}"})
    return flipped


def contrastive_pair_id(base_scenario_id: str, axis: ContrastiveAxis) -> str:
    """Deterministic id shared by both halves of a contrastive pair."""
    digest = hashlib.sha256(f"{base_scenario_id}|{axis.value}".encode()).hexdigest()
    return f"pair-{digest[:24]}"
