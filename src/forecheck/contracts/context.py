"""The structured context a forecheck client submits for one proposed agent action.

Design rule: every field that the policy engine may branch on is *typed*, and every
field that carries attacker-controllable text is explicitly labelled with a
:class:`~forecheck.contracts.enums.TrustLevel`. Free text without a trust label is not
accepted anywhere in this contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from forecheck.contracts.enums import (
    AuthMethod,
    DestinationRelationship,
    OperationKind,
    PrincipalType,
    ResourceKind,
    Sensitivity,
    Stage,
    ToolFamily,
    TrustLevel,
)
from forecheck.contracts.limits import Limits

__all__ = [
    "ActionContext",
    "AffectedResource",
    "AgentIdentity",
    "Destination",
    "Environment",
    "FinancialExposure",
    "Observation",
    "PolicyStatement",
    "Principal",
    "ProposedAction",
    "TrajectoryStep",
    "UserObjective",
]

ShortStr = Annotated[str, Field(max_length=Limits.SHORT_STR)]
MediumStr = Annotated[str, Field(max_length=Limits.MEDIUM_STR)]
LongStr = Annotated[str, Field(max_length=Limits.LONG_STR)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class UserObjective(_Frozen):
    """What the authenticated human actually asked for."""

    text: LongStr
    stated_at: datetime | None = None
    authorization_explicit: bool = Field(
        default=False,
        description=(
            "True only when the principal explicitly authorised this class of action. "
            "Inferring authorisation from a broad objective must set this False."
        ),
    )
    trust: TrustLevel = TrustLevel.PRINCIPAL


class Principal(_Frozen):
    """The authenticated identity on whose behalf the agent is acting."""

    id: ShortStr
    type: PrincipalType = PrincipalType.HUMAN
    tenant_id: ShortStr | None = None
    roles: list[ShortStr] = Field(default_factory=list, max_length=Limits.MAX_ROLES)
    entitlements: list[ShortStr] = Field(
        default_factory=list,
        max_length=Limits.MAX_ENTITLEMENTS,
        description="Fine-grained grants held by the principal, e.g. 'billing:refund:<=500'.",
    )
    auth_method: AuthMethod = AuthMethod.UNKNOWN
    mfa_satisfied: bool | None = None


class AgentIdentity(_Frozen):
    """The agent, and the subset of the principal's authority delegated to it.

    ``delegated_scopes`` is the security-relevant field: an action inside the
    principal's entitlements but outside the agent's delegated scopes is a
    confused-deputy case, not an authorised one.
    """

    id: ShortStr
    name: ShortStr | None = None
    version: ShortStr | None = None
    delegated_scopes: list[ShortStr] = Field(default_factory=list, max_length=Limits.MAX_SCOPES)
    on_behalf_of: ShortStr | None = None


class Observation(_Frozen):
    """Content the agent has read. Trust level decides whether it may steer behaviour."""

    id: ShortStr
    source: ShortStr
    trust: TrustLevel
    content: LongStr
    retrieved_at: datetime | None = None
    content_type: ShortStr | None = None


class TrajectoryStep(_Frozen):
    """One completed tool call earlier in the same session."""

    index: int = Field(ge=0)
    tool_name: ShortStr
    arguments_digest: ShortStr | None = Field(
        default=None,
        description="Digest rather than raw arguments, so callers can supply history "
        "without re-sending secrets. Raw arguments may be supplied instead.",
    )
    arguments: dict[str, Any] | None = None
    outcome: ShortStr | None = None
    result_summary: MediumStr | None = None
    result_trust: TrustLevel = TrustLevel.UNKNOWN
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def _require_some_argument_record(self) -> TrajectoryStep:
        if self.arguments is None and self.arguments_digest is None:
            object.__setattr__(self, "arguments_digest", "")
        return self


class ProposedAction(_Frozen):
    """The tool call about to be executed. This is what forecheck scores."""

    tool_name: ShortStr
    tool_description: MediumStr | None = None
    tool_family: ToolFamily | None = None
    tool_schema_digest: ShortStr | None = Field(
        default=None,
        description="Digest of the tool's declared JSON schema. A change between "
        "sessions is a rug-pull signal; forecheck records it but does not fetch it.",
    )
    arguments: dict[str, Any] = Field(default_factory=dict)
    server: ShortStr | None = Field(
        default=None, description="MCP server or provider identifier, when applicable."
    )
    idempotent: bool | None = None


class AffectedResource(_Frozen):
    """A resource the proposed action touches, and how."""

    urn: ShortStr
    kind: ResourceKind = ResourceKind.OTHER
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    operation: OperationKind = OperationKind.READ
    reversible: bool | None = Field(
        default=None,
        description="None means unknown, which is treated as irreversible by the "
        "conservative policy bundle.",
    )
    record_count_estimate: int | None = Field(default=None, ge=0)
    owner: ShortStr | None = None


class Destination(_Frozen):
    """Where data or a message is going, if anywhere."""

    identifier: ShortStr
    relationship: DestinationRelationship = DestinationRelationship.UNKNOWN_EXTERNAL
    trust: TrustLevel = TrustLevel.UNKNOWN
    resembles: ShortStr | None = Field(
        default=None,
        description="Known identifier this destination resembles, set by the caller's "
        "own look-alike detector. forecheck does not resolve DNS.",
    )
    verified: bool | None = None


class PolicyStatement(_Frozen):
    """One organizational rule, supplied per-request or per-tenant.

    Supplied as natural language because that is how organizations actually hold
    policy. The model scores ``policy_conflict`` against it; the policy engine's own
    rules are separate, typed and deterministic.
    """

    id: ShortStr
    text: MediumStr
    scope: ShortStr | None = None
    severity: ShortStr | None = None


class Environment(_Frozen):
    stage: Stage = Stage.PRODUCTION
    region: ShortStr | None = None
    change_freeze: bool = False
    labels: dict[ShortStr, ShortStr] = Field(default_factory=dict)


class FinancialExposure(_Frozen):
    """Monetary consequence of the action, when the caller can compute it."""

    amount: float = Field(ge=0)
    currency: Annotated[str, Field(min_length=3, max_length=3)] = "USD"
    recurring: bool = False
    counterparty: ShortStr | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class ActionContext(_Frozen):
    """Everything forecheck is given about one proposed action."""

    objective: UserObjective
    principal: Principal
    agent: AgentIdentity
    proposed_action: ProposedAction
    environment: Environment = Field(default_factory=Environment)
    trajectory: list[TrajectoryStep] = Field(
        default_factory=list, max_length=Limits.MAX_TRAJECTORY_STEPS
    )
    observations: list[Observation] = Field(
        default_factory=list, max_length=Limits.MAX_OBSERVATIONS
    )
    resources: list[AffectedResource] = Field(default_factory=list, max_length=Limits.MAX_RESOURCES)
    destination: Destination | None = None
    policies: list[PolicyStatement] = Field(default_factory=list, max_length=Limits.MAX_POLICIES)
    financial: FinancialExposure | None = None

    @model_validator(mode="after")
    def _trajectory_indices_are_ordered(self) -> ActionContext:
        indices = [s.index for s in self.trajectory]
        if indices != sorted(indices):
            raise ValueError("trajectory steps must be supplied in ascending index order")
        return self

    @property
    def has_untrusted_content(self) -> bool:
        return any(o.trust is TrustLevel.UNTRUSTED for o in self.observations) or any(
            s.result_trust is TrustLevel.UNTRUSTED for s in self.trajectory
        )

    @property
    def max_sensitivity(self) -> Sensitivity | None:
        if not self.resources:
            return None
        from forecheck.contracts.enums import SENSITIVITY_ORDER

        return max(self.resources, key=lambda r: SENSITIVITY_ORDER[r.sensitivity]).sensitivity
