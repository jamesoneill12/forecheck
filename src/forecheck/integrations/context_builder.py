"""A fluent builder for :class:`~forecheck.contracts.ActionContext`.

The threat model's A1/A2 assumptions (see ``docs/threat-model.md``) are only as good as
the caller's discipline in setting trust labels and delegated scopes. This builder
cannot make that discipline mandatory, but it can make lapses hard to miss: ``build()``
emits :class:`ForecheckContextWarning` whenever a field that is easy to forget is left
at a value that silently defeats the model.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any

from forecheck.contracts import (
    ActionContext,
    AffectedResource,
    AgentIdentity,
    Destination,
    DestinationRelationship,
    Environment,
    FinancialExposure,
    Observation,
    OperationKind,
    PolicyStatement,
    Principal,
    PrincipalType,
    ProposedAction,
    ResourceKind,
    Sensitivity,
    Stage,
    ToolFamily,
    TrajectoryStep,
    TrustLevel,
    UserObjective,
)
from forecheck.contracts.enums import AuthMethod
from forecheck.integrations.digest import argument_digest

__all__ = ["ActionContextBuilder", "ForecheckContextWarning"]


class ForecheckContextWarning(UserWarning):
    """Raised by :meth:`ActionContextBuilder.build` for likely-forgotten trust labels
    or scopes. Not raised for contract violations, which are Pydantic errors instead."""


class ActionContextBuilder:
    """Accumulates the pieces of an :class:`ActionContext` and assembles them in
    ``build()``. Every setter returns ``self`` so calls can be chained."""

    def __init__(self) -> None:
        self._objective: UserObjective | None = None
        self._principal: Principal | None = None
        self._agent: AgentIdentity | None = None
        self._proposed_action: ProposedAction | None = None
        self._environment: Environment | None = None
        self._trajectory: list[TrajectoryStep] = []
        self._observations: list[Observation] = []
        self._resources: list[AffectedResource] = []
        self._destination: Destination | None = None
        self._policies: list[PolicyStatement] = []
        self._financial: FinancialExposure | None = None

    def objective(self, text: str, explicit: bool = False) -> ActionContextBuilder:
        self._objective = UserObjective(text=text, authorization_explicit=explicit)
        return self

    def principal(
        self,
        id: str,
        *,
        type: PrincipalType = PrincipalType.HUMAN,
        tenant_id: str | None = None,
        roles: list[str] | None = None,
        entitlements: list[str] | None = None,
        auth_method: AuthMethod = AuthMethod.UNKNOWN,
        mfa_satisfied: bool | None = None,
    ) -> ActionContextBuilder:
        self._principal = Principal(
            id=id,
            type=type,
            tenant_id=tenant_id,
            roles=roles or [],
            entitlements=entitlements or [],
            auth_method=auth_method,
            mfa_satisfied=mfa_satisfied,
        )
        return self

    def agent(
        self,
        id: str,
        *,
        name: str | None = None,
        version: str | None = None,
        delegated_scopes: list[str] | None = None,
        on_behalf_of: str | None = None,
    ) -> ActionContextBuilder:
        self._agent = AgentIdentity(
            id=id,
            name=name,
            version=version,
            delegated_scopes=delegated_scopes or [],
            on_behalf_of=on_behalf_of,
        )
        return self

    def observe(
        self,
        source: str,
        content: str,
        trust: TrustLevel = TrustLevel.UNTRUSTED,
        *,
        content_type: str | None = None,
        retrieved_at: datetime | None = None,
    ) -> ActionContextBuilder:
        observation = Observation(
            id=f"obs-{len(self._observations)}",
            source=source,
            trust=trust,
            content=content,
            content_type=content_type,
            retrieved_at=retrieved_at,
        )
        self._observations.append(observation)
        return self

    def step(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        result_summary: str | None = None,
        result_trust: TrustLevel = TrustLevel.UNKNOWN,
        *,
        outcome: str | None = None,
        occurred_at: datetime | None = None,
    ) -> ActionContextBuilder:
        digest = argument_digest(arguments) if arguments is not None else None
        step = TrajectoryStep(
            index=len(self._trajectory),
            tool_name=tool_name,
            arguments=arguments,
            arguments_digest=digest,
            outcome=outcome,
            result_summary=result_summary,
            result_trust=result_trust,
            occurred_at=occurred_at,
        )
        self._trajectory.append(step)
        return self

    def propose(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        description: str | None = None,
        family: ToolFamily | None = None,
        schema_digest: str | None = None,
        *,
        server: str | None = None,
        idempotent: bool | None = None,
    ) -> ActionContextBuilder:
        self._proposed_action = ProposedAction(
            tool_name=tool_name,
            tool_description=description,
            tool_family=family,
            tool_schema_digest=schema_digest,
            arguments=arguments or {},
            server=server,
            idempotent=idempotent,
        )
        return self

    def resource(
        self,
        urn: str,
        *,
        kind: ResourceKind = ResourceKind.OTHER,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        operation: OperationKind = OperationKind.READ,
        reversible: bool | None = None,
        record_count_estimate: int | None = None,
        owner: str | None = None,
    ) -> ActionContextBuilder:
        self._resources.append(
            AffectedResource(
                urn=urn,
                kind=kind,
                sensitivity=sensitivity,
                operation=operation,
                reversible=reversible,
                record_count_estimate=record_count_estimate,
                owner=owner,
            )
        )
        return self

    def destination(
        self,
        identifier: str,
        *,
        relationship: DestinationRelationship = DestinationRelationship.UNKNOWN_EXTERNAL,
        trust: TrustLevel = TrustLevel.UNKNOWN,
        resembles: str | None = None,
        verified: bool | None = None,
    ) -> ActionContextBuilder:
        self._destination = Destination(
            identifier=identifier,
            relationship=relationship,
            trust=trust,
            resembles=resembles,
            verified=verified,
        )
        return self

    def policy(
        self, id: str, text: str, *, scope: str | None = None, severity: str | None = None
    ) -> ActionContextBuilder:
        self._policies.append(PolicyStatement(id=id, text=text, scope=scope, severity=severity))
        return self

    def env(
        self,
        stage: Stage = Stage.PRODUCTION,
        change_freeze: bool = False,
        *,
        region: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> ActionContextBuilder:
        self._environment = Environment(
            stage=stage, region=region, change_freeze=change_freeze, labels=labels or {}
        )
        return self

    def financial(
        self,
        amount: float,
        currency: str = "USD",
        *,
        recurring: bool = False,
        counterparty: str | None = None,
    ) -> ActionContextBuilder:
        self._financial = FinancialExposure(
            amount=amount, currency=currency, recurring=recurring, counterparty=counterparty
        )
        return self

    def _warn_forgotten_assumptions(self) -> None:
        agent = self._agent
        if agent is not None and not agent.delegated_scopes:
            warnings.warn(
                "agent.delegated_scopes is empty: every action will look like a "
                "confused-deputy candidate to the policy engine",
                ForecheckContextWarning,
                stacklevel=3,
            )
        if any(o.trust is TrustLevel.UNKNOWN for o in self._observations):
            warnings.warn(
                "an observation has trust=UNKNOWN; prefer UNTRUSTED unless the source "
                "is genuinely known to be trustworthy",
                ForecheckContextWarning,
                stacklevel=3,
            )
        if self._resources and all(r.sensitivity is Sensitivity.INTERNAL for r in self._resources):
            warnings.warn(
                "all resources are left at the default sensitivity (internal); set it "
                "explicitly or sensitive_data_exposure cannot be scored meaningfully",
                ForecheckContextWarning,
                stacklevel=3,
            )
        if self._destination is not None and self._destination.trust is TrustLevel.UNKNOWN:
            warnings.warn(
                "destination.trust is UNKNOWN; the conservative policy bundle treats "
                "this as untrusted, so set it explicitly if it is not",
                ForecheckContextWarning,
                stacklevel=3,
            )

    def build(self) -> ActionContext:
        objective = self._objective
        principal = self._principal
        agent = self._agent
        proposed_action = self._proposed_action
        if objective is None or principal is None or agent is None or proposed_action is None:
            missing = [
                name
                for name, value in (
                    ("objective", objective),
                    ("principal", principal),
                    ("agent", agent),
                    ("proposed_action", proposed_action),
                )
                if value is None
            ]
            raise ValueError(
                f"ActionContextBuilder.build() is missing required field(s): {', '.join(missing)}"
            )
        self._warn_forgotten_assumptions()
        return ActionContext(
            objective=objective,
            principal=principal,
            agent=agent,
            proposed_action=proposed_action,
            environment=self._environment or Environment(),
            trajectory=list(self._trajectory),
            observations=list(self._observations),
            resources=list(self._resources),
            destination=self._destination,
            policies=list(self._policies),
            financial=self._financial,
        )
