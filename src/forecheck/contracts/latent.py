"""The latent scenario: the machine-checkable facts a synthetic example is built from.

The pipeline runs latent -> labels (deterministic) and latent -> rendered text (LLM or
template), never text -> labels. This keeps ground truth independent of any teacher
model, makes minimal contrastive pairs exact rather than approximate, and means a
labelling bug is a code bug we can unit-test.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecheck.contracts.enums import (
    DestinationRelationship,
    OperationKind,
    ResourceKind,
    Sensitivity,
    Stage,
    ToolFamily,
    TrustLevel,
)

__all__ = [
    "ActionOrigin",
    "AuthorizationBasis",
    "ContextGap",
    "DifficultyTier",
    "LatentScenario",
    "PolicyPredicate",
    "PolicyPredicateKind",
    "SequencePattern",
    "ToolSpec",
]

ShortStr = Annotated[str, Field(max_length=512)]


class ActionOrigin(StrEnum):
    """Whose instruction the proposed action traces back to."""

    PRINCIPAL_REQUEST = "principal_request"
    AGENT_INFERENCE = "agent_inference"
    INJECTED_INSTRUCTION = "injected_instruction"
    COMPROMISED_TOOL_SCHEMA = "compromised_tool_schema"


class AuthorizationBasis(StrEnum):
    EXPLICIT = "explicit"
    IMPLIED_BY_OBJECTIVE = "implied_by_objective"
    ABSENT = "absent"


class SequencePattern(StrEnum):
    """Shape of the preceding trajectory.

    ``BENIGN_*`` members exist so that a positive ``suspicious_action_sequence`` label
    is never inferable from trajectory length alone.
    """

    NONE = "none"
    BENIGN_LINEAR_TASK = "benign_linear_task"
    BENIGN_RETRY_AFTER_ERROR = "benign_retry_after_error"
    BENIGN_BROAD_READ_THEN_SUMMARY = "benign_broad_read_then_summary"
    RECON_THEN_COLLECT_THEN_EXFILTRATE = "recon_then_collect_then_exfiltrate"
    PERMISSION_PROBE_THEN_ESCALATE = "permission_probe_then_escalate"
    DISABLE_CONTROL_THEN_ACT = "disable_control_then_act"
    SPLIT_THRESHOLD_EVASION = "split_threshold_evasion"
    CREDENTIAL_HARVEST_THEN_PIVOT = "credential_harvest_then_pivot"
    SCHEMA_SWAP_THEN_REUSE = "schema_swap_then_reuse"


ATTACK_SEQUENCE_PATTERNS: frozenset[SequencePattern] = frozenset(
    {
        SequencePattern.RECON_THEN_COLLECT_THEN_EXFILTRATE,
        SequencePattern.PERMISSION_PROBE_THEN_ESCALATE,
        SequencePattern.DISABLE_CONTROL_THEN_ACT,
        SequencePattern.SPLIT_THRESHOLD_EVASION,
        SequencePattern.CREDENTIAL_HARVEST_THEN_PIVOT,
        SequencePattern.SCHEMA_SWAP_THEN_REUSE,
    }
)


class ContextGap(StrEnum):
    """A causally relevant fact deliberately withheld from the rendered example."""

    NONE = "none"
    MISSING_POLICY = "missing_policy"
    MISSING_PRINCIPAL_ENTITLEMENTS = "missing_principal_entitlements"
    MISSING_DELEGATED_SCOPES = "missing_delegated_scopes"
    MISSING_RESOURCE_SENSITIVITY = "missing_resource_sensitivity"
    MISSING_DESTINATION_TRUST = "missing_destination_trust"
    MISSING_REVERSIBILITY = "missing_reversibility"
    MISSING_OBJECTIVE = "missing_objective"


class DifficultyTier(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


class PolicyPredicateKind(StrEnum):
    """Machine-checkable form of an organizational policy statement."""

    FORBID_TOOL = "forbid_tool"
    FORBID_OPERATION_ON_SENSITIVITY = "forbid_operation_on_sensitivity"
    FORBID_EXTERNAL_DESTINATION = "forbid_external_destination"
    FORBID_IN_STAGE = "forbid_in_stage"
    REQUIRE_EXPLICIT_AUTHORIZATION = "require_explicit_authorization"
    MAX_FINANCIAL_AMOUNT = "max_financial_amount"
    FORBID_ROLE = "forbid_role"
    REQUIRE_CHANGE_WINDOW = "require_change_window"
    FORBID_BULK_ABOVE_N = "forbid_bulk_above_n"
    REQUIRE_TICKET_REFERENCE = "require_ticket_reference"
    FORBID_OUTSIDE_BUSINESS_HOURS = "forbid_outside_business_hours"
    FORBID_RECIPIENT_DOMAIN = "forbid_recipient_domain"
    REQUIRE_DRY_RUN_FIRST = "require_dry_run_first"
    DATA_RESIDENCY_REGION = "data_residency_region"
    FORBID_PII_FIELD_EXPORT = "forbid_pii_field_export"


class PolicyPredicate(BaseModel):
    """One organizational rule in evaluable form.

    ``violated`` is computed by :mod:`forecheck.data.labeling`, not asserted by the
    generator, so a predicate cannot silently disagree with the scenario it describes.

    ``paraphrase_index`` selects which surface clause paraphrase (see
    ``forecheck.data.rendering``) is used to render this predicate's text. It lives on
    the predicate, not the surface, so the policy-generalisation splits can key on it
    without touching rendered text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: ShortStr
    kind: PolicyPredicateKind
    paraphrase_index: int = Field(default=0, ge=0)
    tool_name: ShortStr | None = None
    operation: OperationKind | None = None
    min_sensitivity: Sensitivity | None = None
    stage: Stage | None = None
    max_amount: float | None = Field(default=None, ge=0)
    role: ShortStr | None = None
    severity: ShortStr = "medium"
    max_record_count: int | None = Field(default=None, ge=0)
    business_hour_start: int | None = Field(default=None, ge=0, le=23)
    business_hour_end: int | None = Field(default=None, ge=0, le=23)
    allowed_domains: list[ShortStr] = Field(default_factory=list)
    allowed_regions: list[ShortStr] = Field(default_factory=list)
    pii_fields: list[ShortStr] = Field(default_factory=list)


class ToolSpec(BaseModel):
    """Intrinsic properties of a tool, independent of who calls it or why."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: ShortStr
    family: ToolFamily
    operation: OperationKind
    required_scopes: list[ShortStr] = Field(default_factory=list)
    resource_kind: ResourceKind = ResourceKind.OTHER
    is_communication: bool = False
    is_financial: bool = False
    changes_authority: bool = False
    intrinsically_irreversible: bool = False
    idempotent: bool = True
    summary: ShortStr = ""


class LatentScenario(BaseModel):
    """Complete causal description of one example.

    Two scenarios differing in exactly one field render a minimal contrastive pair; the
    label delta between them is then provably attributable to that field.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: ShortStr
    family_id: ShortStr = Field(
        description="Scenario family. Splits are taken on this, never on rows."
    )
    template_lineage: list[ShortStr] = Field(
        default_factory=list,
        description="Ancestry of templates used, so descendants of a shared template "
        "cannot straddle a split boundary.",
    )

    tool: ToolSpec
    operation: OperationKind

    principal_roles: list[ShortStr] = Field(default_factory=list)
    principal_entitlements: list[ShortStr] = Field(default_factory=list)
    agent_delegated_scopes: list[ShortStr] = Field(default_factory=list)
    required_scopes: list[ShortStr] = Field(default_factory=list)

    authorization_basis: AuthorizationBasis = AuthorizationBasis.IMPLIED_BY_OBJECTIVE
    action_origin: ActionOrigin = ActionOrigin.PRINCIPAL_REQUEST

    resource_sensitivity: Sensitivity = Sensitivity.INTERNAL
    resource_reversible: bool = True
    record_count: int = Field(default=1, ge=0)

    destination_present: bool = False
    destination_relationship: DestinationRelationship = DestinationRelationship.SELF
    destination_trust: TrustLevel = TrustLevel.TRUSTED_TOOL

    stage: Stage = Stage.PRODUCTION
    change_freeze: bool = False
    local_hour: int = Field(default=12, ge=0, le=23)
    resource_region: str = "us-east-1"

    financial_amount: float = Field(default=0.0, ge=0.0)
    financial_currency: str = "USD"
    financial_material_threshold: float = Field(
        default=100.0,
        ge=0.0,
        description="Amount above which the organization treats the commitment as "
        "material. Rendered into policy text so the model can learn the boundary "
        "rather than memorise a constant.",
    )

    untrusted_content_present: bool = False
    untrusted_content_contains_instruction: bool = False

    authority_before: list[ShortStr] = Field(default_factory=list)
    authority_after: list[ShortStr] = Field(default_factory=list)

    recipient_domain: str | None = None
    ticket_reference: ShortStr | None = None
    dry_run_performed: bool = False
    touched_pii_fields: list[ShortStr] = Field(default_factory=list)

    policy_predicates: list[PolicyPredicate] = Field(default_factory=list)
    policy_supplied: bool = True

    sequence_pattern: SequencePattern = SequencePattern.NONE
    trajectory_length: int = Field(default=0, ge=0)

    context_gaps: list[ContextGap] = Field(default_factory=list)
    difficulty: DifficultyTier = DifficultyTier.MEDIUM
    is_benign_hard_negative: bool = False
    notes: ShortStr = ""

    @model_validator(mode="after")
    def _injection_requires_untrusted_content(self) -> LatentScenario:
        if self.action_origin is ActionOrigin.INJECTED_INSTRUCTION and not (
            self.untrusted_content_present and self.untrusted_content_contains_instruction
        ):
            raise ValueError(
                "action_origin=injected_instruction requires untrusted content that "
                "contains an instruction"
            )
        if self.untrusted_content_contains_instruction and not self.untrusted_content_present:
            raise ValueError("untrusted instruction requires untrusted content")
        if not self.destination_present and self.destination_relationship not in (
            DestinationRelationship.SELF,
        ):
            raise ValueError(
                "destination_relationship must be 'self' when no destination is present"
            )
        return self

    @property
    def effective_scopes(self) -> frozenset[str]:
        """Authority actually available: the principal's entitlements narrowed by
        what was delegated to the agent."""
        return frozenset(self.principal_entitlements) & frozenset(self.agent_delegated_scopes)
