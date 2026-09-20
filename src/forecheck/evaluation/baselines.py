"""Baseline backends: a deterministic rule system, and adapter skeletons for judges.

``RuleBaselineBackend`` answers the question "what does a purely deterministic system,
using only the typed facts the policy engine would also see, get you?" It is the floor
a learned model must clear to justify its own existence, and it is useful precisely
because it has zero learned parameters and is trivially auditable.

The judge adapters are the opposite extreme: no typed reasoning at all, a generative
model asked a yes/no question per dimension. They are intentionally uncalibrated (a
"yes" maps to ``1.0`` and a "no" to ``0.0``, not a probability) and are never exercised
against a real network in this test suite.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from forecheck.contracts import (
    LABEL_SCHEMA_VERSION,
    DestinationRelationship,
    ModelInfo,
    OperationKind,
    RiskDimension,
    Sensitivity,
    TruncationInfo,
    TrustLevel,
)
from forecheck.inference.base import BackendCapabilities, RawScores

if TYPE_CHECKING:
    from forecheck.contracts import ActionContext

__all__ = [
    "JevBackend",
    "LLMJudgeBackend",
    "NimbleBackend",
    "RuleBaselineBackend",
]

_HIGH = 0.95
_MID = 0.5
_LOW = 0.05

_ESCALATION_OPERATIONS = frozenset({OperationKind.GRANT, OperationKind.REVOKE})
_EXTERNAL_DESTINATIONS = frozenset(
    {DestinationRelationship.UNKNOWN_EXTERNAL, DestinationRelationship.LOOKALIKE}
)
_SENSITIVE_TIERS = frozenset({Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED, Sensitivity.SECRET})


def _rule_prompt_injection_influence(context: ActionContext) -> float:
    return _HIGH if context.has_untrusted_content else _LOW


def _rule_unauthorized_scope(context: ActionContext) -> float:
    if not context.agent.delegated_scopes:
        return _HIGH
    if not context.objective.authorization_explicit:
        return _MID
    return _LOW


def _rule_sensitive_data_exposure(context: ActionContext) -> float:
    max_sensitivity = context.max_sensitivity
    if max_sensitivity is None:
        return _LOW
    destination = context.destination
    if (
        max_sensitivity in _SENSITIVE_TIERS
        and destination is not None
        and (destination.trust in (TrustLevel.UNTRUSTED, TrustLevel.UNKNOWN))
    ):
        return _HIGH
    if max_sensitivity in _SENSITIVE_TIERS:
        return _MID
    return _LOW


def _rule_untrusted_destination(context: ActionContext) -> float:
    destination = context.destination
    if destination is None:
        return _LOW
    if destination.relationship in _EXTERNAL_DESTINATIONS:
        return _HIGH
    if destination.trust is TrustLevel.UNKNOWN:
        return _MID
    return _LOW


def _rule_privilege_escalation(context: ActionContext) -> float:
    if any(r.operation in _ESCALATION_OPERATIONS for r in context.resources):
        return _HIGH
    return _LOW


def _rule_destructive_or_irreversible_action(context: ActionContext) -> float:
    for resource in context.resources:
        if resource.reversible is False:
            return _HIGH
        if resource.reversible is None and resource.operation is OperationKind.DELETE:
            return _HIGH
    if any(r.operation is OperationKind.DELETE for r in context.resources):
        return _MID
    return _LOW


def _rule_financial_commitment(context: ActionContext) -> float:
    if context.financial is not None and context.financial.amount > 0:
        return _HIGH
    return _LOW


def _rule_external_communication(context: ActionContext) -> float:
    destination = context.destination
    if destination is None:
        return _LOW
    if destination.relationship in (
        DestinationRelationship.KNOWN_THIRD_PARTY,
        DestinationRelationship.UNKNOWN_EXTERNAL,
        DestinationRelationship.LOOKALIKE,
    ):
        return _HIGH
    if destination.relationship is DestinationRelationship.SAME_TENANT:
        return _MID
    return _LOW


def _rule_policy_conflict(context: ActionContext) -> float:
    """Cannot parse natural-language policy text with typed rules alone.

    Always ``_MID``: this dimension is deliberately baseline-uninformative, which is
    itself the honest answer for a rule system with no NLP.
    """
    return _MID if context.policies else _LOW


def _rule_suspicious_action_sequence(context: ActionContext) -> float:
    length = len(context.trajectory)
    if length >= 4:
        return _HIGH
    if length >= 1:
        return _MID
    return _LOW


def _rule_insufficient_context(context: ActionContext) -> float:
    if context.destination is None and not context.resources and context.financial is None:
        return _HIGH
    return _LOW


_RULES: dict[RiskDimension, Callable[[ActionContext], float]] = {
    RiskDimension.PROMPT_INJECTION_INFLUENCE: _rule_prompt_injection_influence,
    RiskDimension.UNAUTHORIZED_SCOPE: _rule_unauthorized_scope,
    RiskDimension.SENSITIVE_DATA_EXPOSURE: _rule_sensitive_data_exposure,
    RiskDimension.UNTRUSTED_DESTINATION: _rule_untrusted_destination,
    RiskDimension.PRIVILEGE_ESCALATION: _rule_privilege_escalation,
    RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: _rule_destructive_or_irreversible_action,
    RiskDimension.FINANCIAL_COMMITMENT: _rule_financial_commitment,
    RiskDimension.EXTERNAL_COMMUNICATION: _rule_external_communication,
    RiskDimension.POLICY_CONFLICT: _rule_policy_conflict,
    RiskDimension.SUSPICIOUS_ACTION_SEQUENCE: _rule_suspicious_action_sequence,
    RiskDimension.INSUFFICIENT_CONTEXT: _rule_insufficient_context,
}


class RuleBaselineBackend:
    """A :class:`~forecheck.inference.base.ClassifierBackend` with zero learned parameters.

    Each dimension is scored in ``{0.05, 0.5, 0.95}`` by a hand-written rule over typed
    :class:`~forecheck.contracts.context.ActionContext` facts — the same *kind* of facts
    a :class:`~forecheck.policies.base.PolicyEngine` uses. It never reads free text.
    """

    def __init__(self) -> None:
        self._model_info = ModelInfo(
            backend="rule_baseline",
            model_id="rule-baseline-v1",
            prompt_contract_hash="n/a",
            label_schema_version=LABEL_SCHEMA_VERSION,
        )

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_batching=True, deterministic=True)

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        scores = {dimension: _RULES[dimension](context) for dimension in dims}
        return RawScores(scores=scores, truncation=TruncationInfo())

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]:
        return [self.score(c, dimensions) for c in contexts]

    def warmup(self) -> None:
        return None

    def close(self) -> None:
        return None


class LLMJudgeBackend:
    """Uncalibrated adapter over a generative model asked one yes/no question per dimension.

    ``chat_fn`` is injected by the caller (a real client, or a fake in tests); this
    class performs no network I/O itself. Any real deployment's model name or endpoint
    should come from the environment (e.g. ``FORECHECK_LLM_JUDGE_MODEL``), never a
    hardcoded default, so that credentials and endpoints stay out of source control.
    A "yes" answer maps to raw score ``1.0`` and "no" to ``0.0`` — these are **not**
    probabilities, and this backend's ``capabilities.deterministic`` is ``False``.
    """

    def __init__(
        self,
        chat_fn: Callable[[str], str],
        *,
        model_id: str | None = None,
    ) -> None:
        self._chat_fn = chat_fn
        self._model_id = model_id or os.environ.get("FORECHECK_LLM_JUDGE_MODEL", "llm-judge")
        self._model_info = ModelInfo(
            backend="llm_judge",
            model_id=self._model_id,
            prompt_contract_hash="n/a",
            label_schema_version=LABEL_SCHEMA_VERSION,
        )

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_batching=False, deterministic=False)

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        scores: dict[RiskDimension, float] = {}
        abstained: set[RiskDimension] = set()
        for dimension in dims:
            reply = self._chat_fn(self._build_prompt(dimension, context))
            parsed = self._parse_yes_no(reply)
            if parsed is None:
                abstained.add(dimension)
            else:
                scores[dimension] = 1.0 if parsed else 0.0
        return RawScores(
            scores=scores,
            truncation=TruncationInfo(),
            abstained_dimensions=frozenset(abstained),
        )

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]:
        return [self.score(c, dimensions) for c in contexts]

    def warmup(self) -> None:
        return None

    def close(self) -> None:
        return None

    def _build_prompt(self, dimension: RiskDimension, context: ActionContext) -> str:
        return (
            f"Does the following proposed action exhibit '{dimension.value}'? "
            f"Answer yes or no only.\nTool: {context.proposed_action.tool_name}\n"
            f"Objective: {context.objective.text}"
        )

    def _parse_yes_no(self, reply: str) -> bool | None:
        normalized = reply.strip().lower()
        if normalized.startswith("yes"):
            return True
        if normalized.startswith("no"):
            return False
        return None


class NimbleBackend:
    """Extension point for a Nimble-hosted guardrail model. Not implemented.

    Optional: wiring this up requires a licence and API-key review before any network
    call is added, and it is intentionally not part of the default test suite. This
    class exists only to reserve the adapter's shape.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "NimbleBackend requires a licence/API-key review before implementation."
        )


class JevBackend:
    """Extension point for a Jev-hosted guardrail model. Not implemented.

    Optional: wiring this up requires a licence and API-key review before any network
    call is added, and it is intentionally not part of the default test suite. This
    class exists only to reserve the adapter's shape.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "JevBackend requires a licence/API-key review before implementation."
        )
