"""A deterministic, heuristic mock backend.

``MockBackend`` is **not a trained model and is not fit for production**. It exists so
the API, calibration, and policy layers can be exercised end-to-end without a real
classifier. Every score comes from a transparent per-dimension rule applied to the
typed :class:`~forecheck.contracts.ActionContext` fields (see the ``_score_*``
functions below for the rule each dimension uses), then a small deterministic seeded
jitter -- a hash of the rendered context text, the dimension, and the configured seed
-- so scores are not degenerate constants and a calibrator has something to fit.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from forecheck.contracts import (
    LABEL_SCHEMA_VERSION,
    MUTATING_OPERATIONS,
    SENSITIVITY_ORDER,
    DestinationRelationship,
    ModelInfo,
    OperationKind,
    RiskDimension,
    ToolFamily,
    TrustLevel,
)
from forecheck.inference.base import BackendCapabilities, BaseBackend, RawScores
from forecheck.inference.prompt import prompt_contract_hash
from forecheck.inference.serialization import serialize_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forecheck.contracts import ActionContext

__all__ = ["MockBackend"]

MODEL_ID = "mock-heuristic-v1"

_IMPERATIVE_KEYWORDS: tuple[str, ...] = (
    "ignore",
    "must",
    "immediately",
    "urgent",
    "do not tell",
    "new instructions",
    "override",
    "as system",
    "you should now",
    "disregard",
    "instead, please",
)
_FORBIDDING_KEYWORDS: tuple[str, ...] = (
    "must not",
    "forbidden",
    "not allowed",
    "prohibited",
    "may not",
    "never",
)
_ESCALATION_ROLE_HINTS: tuple[str, ...] = ("admin", "root", "owner", "superuser")
_COMMUNICATION_TOOL_HINTS: tuple[str, ...] = ("email", "message", "send", "notify", "post", "reply")
_JITTER_MAGNITUDE = 0.04


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _jitter(context_text: str, dimension: RiskDimension, seed: int) -> float:
    key = f"{seed}:{dimension.value}:{context_text}".encode()
    digest = hashlib.sha256(key).digest()
    unit = int.from_bytes(digest[:8], "big") / float(2**64)
    return (unit - 0.5) * 2.0 * _JITTER_MAGNITUDE


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(needle in lowered for needle in needles)


def _text_overlap(a: str, b: str, *, min_len: int = 6) -> bool:
    a_words = [w.lower() for w in a.split() if len(w) >= min_len]
    b_lower = b.lower()
    return any(w in b_lower for w in a_words)


def _score_prompt_injection_influence(context: ActionContext) -> float:
    untrusted = [o for o in context.observations if o.trust is TrustLevel.UNTRUSTED]
    if not untrusted:
        return 0.05
    action_text = " ".join(
        [context.proposed_action.tool_name, str(context.proposed_action.arguments)]
    )
    score = 0.05
    for obs in untrusted:
        if _contains_any(obs.content, _IMPERATIVE_KEYWORDS):
            score = max(score, 0.45)
            if _text_overlap(obs.content, action_text):
                score = max(score, 0.85)
    return _clip01(score)


def _score_unauthorized_scope(context: ActionContext) -> float:
    mutating = any(r.operation in MUTATING_OPERATIONS for r in context.resources)
    if not mutating:
        return 0.1
    if not context.agent.delegated_scopes:
        return 0.7
    required_hint = context.proposed_action.tool_name.lower()
    covered = any(required_hint in scope.lower() for scope in context.agent.delegated_scopes)
    return 0.15 if covered else 0.55


def _score_sensitive_data_exposure(context: ActionContext) -> float:
    max_sensitivity = context.max_sensitivity
    if max_sensitivity is None:
        return 0.05
    sensitivity_rank = SENSITIVITY_ORDER[max_sensitivity]
    destination = context.destination
    if destination is None:
        return _clip01(0.05 + 0.05 * sensitivity_rank)
    if destination.trust in (TrustLevel.UNTRUSTED, TrustLevel.UNKNOWN):
        return _clip01(0.3 + 0.15 * sensitivity_rank)
    return _clip01(0.05 + 0.05 * sensitivity_rank)


def _score_untrusted_destination(context: ActionContext) -> float:
    destination = context.destination
    if destination is None:
        return 0.02
    base = {
        DestinationRelationship.SELF: 0.02,
        DestinationRelationship.SAME_TENANT: 0.1,
        DestinationRelationship.KNOWN_THIRD_PARTY: 0.2,
        DestinationRelationship.UNKNOWN_EXTERNAL: 0.65,
        DestinationRelationship.LOOKALIKE: 0.9,
    }[destination.relationship]
    if destination.verified is False:
        base = min(1.0, base + 0.15)
    return _clip01(base)


def _score_privilege_escalation(context: ActionContext) -> float:
    grant_like = any(
        r.operation in (OperationKind.GRANT, OperationKind.REVOKE) for r in context.resources
    )
    role_hint = any(
        _contains_any(role, _ESCALATION_ROLE_HINTS) for role in context.agent.delegated_scopes
    )
    if grant_like and role_hint:
        return 0.85
    if grant_like or role_hint:
        return 0.5
    return 0.05


def _score_destructive_or_irreversible(context: ActionContext) -> float:
    if not context.resources:
        return 0.05
    worst = 0.0
    for r in context.resources:
        if r.operation is OperationKind.DELETE:
            worst = max(worst, 0.8)
        if r.reversible is False:
            worst = max(worst, 0.75)
        elif r.reversible is None:
            worst = max(worst, 0.4)
    return _clip01(worst) if worst else 0.05


def _score_financial_commitment(context: ActionContext) -> float:
    financial = context.financial
    if financial is None:
        return 0.02
    magnitude = _clip01(financial.amount / 1000.0)
    bonus = 0.15 if financial.recurring else 0.0
    return _clip01(0.1 + 0.6 * magnitude + bonus)


def _score_external_communication(context: ActionContext) -> float:
    if context.proposed_action.tool_family is ToolFamily.EMAIL_MESSAGING:
        return 0.75
    if _contains_any(context.proposed_action.tool_name, _COMMUNICATION_TOOL_HINTS):
        return 0.6
    destination = context.destination
    if destination is not None and destination.relationship is not DestinationRelationship.SELF:
        return 0.35
    return 0.05


def _score_policy_conflict(context: ActionContext) -> float:
    if not context.policies:
        return 0.05
    tool_name = context.proposed_action.tool_name.lower()
    for policy in context.policies:
        text_lower = policy.text.lower()
        if tool_name in text_lower and _contains_any(text_lower, _FORBIDDING_KEYWORDS):
            return 0.85
    return 0.1


def _score_suspicious_action_sequence(context: ActionContext) -> float:
    n = len(context.trajectory)
    if n == 0:
        return 0.05
    distinct_tools = len({s.tool_name for s in context.trajectory})
    density = distinct_tools / max(1, n)
    length_component = _clip01(n / 10.0)
    return _clip01(0.1 + 0.4 * length_component + 0.3 * density)


def _score_insufficient_context(context: ActionContext) -> float:
    missing = 0
    total = 4
    if context.destination is None and context.proposed_action.tool_family in (
        ToolFamily.EMAIL_MESSAGING,
        ToolFamily.FILE_STORAGE,
    ):
        missing += 1
    if not context.resources:
        missing += 1
    if not context.policies:
        missing += 1
    if len(context.objective.text) < 8:
        missing += 1
    return _clip01(0.05 + 0.9 * (missing / total))


_SCORERS = {
    RiskDimension.PROMPT_INJECTION_INFLUENCE: _score_prompt_injection_influence,
    RiskDimension.UNAUTHORIZED_SCOPE: _score_unauthorized_scope,
    RiskDimension.SENSITIVE_DATA_EXPOSURE: _score_sensitive_data_exposure,
    RiskDimension.UNTRUSTED_DESTINATION: _score_untrusted_destination,
    RiskDimension.PRIVILEGE_ESCALATION: _score_privilege_escalation,
    RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: _score_destructive_or_irreversible,
    RiskDimension.FINANCIAL_COMMITMENT: _score_financial_commitment,
    RiskDimension.EXTERNAL_COMMUNICATION: _score_external_communication,
    RiskDimension.POLICY_CONFLICT: _score_policy_conflict,
    RiskDimension.SUSPICIOUS_ACTION_SEQUENCE: _score_suspicious_action_sequence,
    RiskDimension.INSUFFICIENT_CONTEXT: _score_insufficient_context,
}


class MockBackend(BaseBackend):
    """Deterministic heuristic backend. Not a trained model; not for production use."""

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            backend="mock",
            model_id=MODEL_ID,
            revision=None,
            base_model=None,
            adapter_id=None,
            prompt_contract_hash=prompt_contract_hash(),
            label_schema_version=LABEL_SCHEMA_VERSION,
            quantization=None,
        )

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_batching=True,
            supports_shared_prefill=False,
            max_prompt_tokens=8192,
            device="cpu",
            deterministic=True,
        )

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        rendered = serialize_context(context)
        scores: dict[RiskDimension, float] = {}
        for dim in dims:
            base = _SCORERS[dim](context)
            scores[dim] = _clip01(base + _jitter(rendered.text, dim, self._seed))
        return RawScores(
            scores=scores,
            truncation=rendered.truncation,
            prompt_tokens=rendered.estimated_tokens,
        )
