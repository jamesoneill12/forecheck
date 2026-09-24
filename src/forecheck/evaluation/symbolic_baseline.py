"""Compiled-predicate symbolic baseline for ``unauthorized_scope``, ``privilege_escalation``
and ``policy_conflict``.

``RuleBaselineBackend`` (see :mod:`forecheck.evaluation.baselines`) is deliberately
uninformative on exactly these three dimensions: it never intersects entitlements with
delegated scope, and it treats every supplied policy as an unparseable constant. This
backend closes that gap using only facts the typed
:class:`~forecheck.contracts.context.ActionContext` already carries (plus the tool
catalogue, which is public metadata a real policy engine would also have):
required-scope lookup for scope authorization, the rendered
authority-before/after arguments for privilege escalation, and regexes inverting the
generator's own policy-clause phrasing templates for policy conflict. Every other
dimension is delegated unchanged to :class:`~forecheck.evaluation.baselines.RuleBaselineBackend`.

The policy-conflict compiler only knows the phrasing templates for policy kinds *not*
withheld by :func:`~forecheck.data.splitting.default_heldout_policy_kinds` -- the same
kinds a model would have seen in training. A clause instantiating a withheld kind's
template, or any clause matching no known template, abstains at ``0.5``; see
:class:`PolicyClauseStats` for the per-clause accounting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from forecheck.contracts import (
    LABEL_SCHEMA_VERSION,
    SENSITIVITY_ORDER,
    DestinationRelationship,
    ModelInfo,
    OperationKind,
    PolicyPredicateKind,
    RiskDimension,
    Sensitivity,
    Stage,
    ToolFamily,
    ToolSpec,
    TruncationInfo,
)
from forecheck.data.rendering import _POLICY_CLAUSE_TEMPLATES, _POLICY_WRAPPER_TEMPLATES
from forecheck.data.splitting import default_heldout_policy_kinds
from forecheck.data.tools import get_tool
from forecheck.evaluation.baselines import RuleBaselineBackend
from forecheck.inference.base import BackendCapabilities, RawScores

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from forecheck.contracts import ActionContext

    _Evaluator = Callable[[dict[str, str], ActionContext], bool | None]

__all__ = ["PolicyClauseStats", "SymbolicBaselineBackend"]

_HIGH = 0.95
_MID = 0.5
_LOW = 0.05

_SAME_TENANCY: frozenset[DestinationRelationship] = frozenset(
    {DestinationRelationship.SELF, DestinationRelationship.SAME_TENANT}
)


def _lookup_tool(context: ActionContext) -> ToolSpec | None:
    try:
        return get_tool(context.proposed_action.tool_name)
    except KeyError:
        return None


def _effective_scopes(context: ActionContext) -> frozenset[str]:
    return frozenset(context.principal.entitlements) & frozenset(context.agent.delegated_scopes)


def _is_destructive(context: ActionContext) -> bool | None:
    tool = _lookup_tool(context)
    if tool is None:
        return None
    if tool.operation is OperationKind.DELETE or tool.intrinsically_irreversible:
        return True
    if not context.resources:
        return None
    return context.resources[0].reversible is False


def symbolic_unauthorized_scope(context: ActionContext) -> float:
    """0.95 iff a required scope of the proposed action is outside entitlements ∩
    delegated scope; 0.05 otherwise. Required scopes come from the tool catalogue, keyed
    by ``proposed_action.tool_name`` -- the same typed lookup a real policy engine would
    make from the tool's registered schema, never from rendered text."""
    tool = _lookup_tool(context)
    if tool is None:
        return _MID
    required = frozenset(tool.required_scopes)
    if not required:
        return _LOW
    return _HIGH if required - _effective_scopes(context) else _LOW


def symbolic_privilege_escalation(context: ActionContext) -> float:
    """Mirrors the generator's own label rule (``forecheck.data.labeling._privilege_escalation``)
    using only typed facts: the ``authority_before``/``authority_after`` arguments the
    renderer attaches to any authority-changing tool call, plus the tool's catalogued
    ``operation`` and ``changes_authority``. When those arguments are absent the tool
    cannot escalate authority by construction, so 0.05 is the correct (not abstained)
    answer, not a guess."""
    args = context.proposed_action.arguments
    before, after = args.get("authority_before"), args.get("authority_after")
    if not isinstance(before, list) or not isinstance(after, list):
        return _LOW
    tool = _lookup_tool(context)
    if tool is None:
        return _LOW
    widened_by_tool = tool.changes_authority and bool(set(after) - set(before))
    granted_new = tool.operation is OperationKind.GRANT and bool(
        set(after) - _effective_scopes(context)
    )
    return _HIGH if widened_by_tool or granted_new else _LOW


_FIELD_PATTERNS: dict[str, str] = {
    "tool_name": r"[\w.\-]+",
    "op": r"[a-z_]+",
    "sensitivity": r"[a-z]+",
    "stage": r"[a-z]+",
    "amount": r"-?\d+(?:\.\d+)?",
    "role": r"[\w\-]+",
    "max_record_count": r"\d+",
    "business_hour_start": r"\d+",
    "business_hour_end": r"\d+",
    "allowed_domains": r".+?",
    "allowed_regions": r".+?",
    "pii_fields": r".+?",
    "forbidden_currencies": r".+?",
    "forbidden_tool_family": r"[a-z_]+",
    "forbidden_export_formats": r".+?",
    "forbidden_channels": r".+?",
    "max_allowed_sensitivity": r"[a-z]+",
    "max_daily_record_count": r"\d+",
}
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _compile_template(template: str) -> re.Pattern[str]:
    """Invert one generator template string into an anchored, case-insensitive regex
    with a named group per ``{placeholder}``, so matching it back against rendered text
    recovers the parameters the generator filled in."""
    parts: list[str] = []
    last = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        parts.append(re.escape(template[last : m.start()]))
        name = m.group(1)
        parts.append(f"(?P<{name}>{_FIELD_PATTERNS.get(name, '.+?')})")
        last = m.end()
    parts.append(re.escape(template[last:]))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


def _list_param(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _eval_forbid_tool(params: dict[str, str], context: ActionContext) -> bool | None:
    return context.proposed_action.tool_name == params["tool_name"]


def _eval_forbid_operation_on_sensitivity(
    params: dict[str, str], context: ActionContext
) -> bool | None:
    try:
        op = OperationKind(params["op"])
        min_sensitivity = Sensitivity(params["sensitivity"])
    except ValueError:
        return None
    tool = _lookup_tool(context)
    sensitivity = context.max_sensitivity
    if tool is None or sensitivity is None:
        return None
    return (
        tool.operation is op
        and SENSITIVITY_ORDER[sensitivity] >= SENSITIVITY_ORDER[min_sensitivity]
    )


def _eval_forbid_external_destination(_: dict[str, str], context: ActionContext) -> bool | None:
    destination = context.destination
    return destination is not None and destination.relationship not in _SAME_TENANCY


def _eval_forbid_in_stage(params: dict[str, str], context: ActionContext) -> bool | None:
    try:
        stage = Stage(params["stage"])
    except ValueError:
        return None
    return context.environment.stage is stage


def _eval_require_explicit_authorization(_: dict[str, str], context: ActionContext) -> bool | None:
    return not context.objective.authorization_explicit


def _financial_amount(context: ActionContext) -> float:
    return context.financial.amount if context.financial is not None else 0.0


def _eval_max_financial_amount(params: dict[str, str], context: ActionContext) -> bool | None:
    try:
        threshold = float(params["amount"])
    except ValueError:
        return None
    return _financial_amount(context) > threshold


def _eval_forbid_role(params: dict[str, str], context: ActionContext) -> bool | None:
    return params["role"] in context.principal.roles


def _eval_require_change_window(_: dict[str, str], context: ActionContext) -> bool | None:
    return context.environment.change_freeze


def _eval_forbid_bulk_above_n(params: dict[str, str], context: ActionContext) -> bool | None:
    try:
        threshold = int(params["max_record_count"])
    except ValueError:
        return None
    if not context.resources:
        return None
    count = context.resources[0].record_count_estimate
    return None if count is None else count > threshold


def _eval_require_ticket_reference(_: dict[str, str], context: ActionContext) -> bool | None:
    return "ticket_reference" not in context.proposed_action.arguments


def _eval_forbid_outside_business_hours(
    params: dict[str, str], context: ActionContext
) -> bool | None:
    try:
        start, end = int(params["business_hour_start"]), int(params["business_hour_end"])
    except ValueError:
        return None
    hour = context.environment.labels.get("local_hour")
    if hour is None:
        return None
    try:
        hour_i = int(hour)
    except ValueError:
        return None
    return not (start <= hour_i < end)


def _eval_forbid_recipient_domain(params: dict[str, str], context: ActionContext) -> bool | None:
    allowed = _list_param(params["allowed_domains"])
    destination = context.destination
    if destination is None or "@" not in destination.identifier:
        return None
    domain = destination.identifier.rsplit("@", 1)[-1]
    return domain not in allowed


def _eval_data_residency_region(params: dict[str, str], context: ActionContext) -> bool | None:
    allowed = _list_param(params["allowed_regions"])
    region = context.environment.region
    return None if region is None else region not in allowed


def _eval_forbid_pii_field_export(params: dict[str, str], context: ActionContext) -> bool | None:
    fields = _list_param(params["pii_fields"])
    if context.destination is None:
        return False
    touched = context.proposed_action.arguments.get("pii_fields")
    touched_set = set(touched) if isinstance(touched, list) else set()
    return bool(fields & touched_set)


def _eval_require_manager_approval_above_amount(
    params: dict[str, str], context: ActionContext
) -> bool | None:
    try:
        threshold = float(params["amount"])
    except ValueError:
        return None
    if _financial_amount(context) <= threshold:
        return False
    approved = context.proposed_action.arguments.get("manager_approved")
    return None if approved is None else not approved


def _eval_forbid_currency(params: dict[str, str], context: ActionContext) -> bool | None:
    forbidden = _list_param(params["forbidden_currencies"])
    if context.financial is None:
        return False
    return context.financial.currency in forbidden


def _eval_require_two_person_rule_for_destructive(
    _: dict[str, str], context: ActionContext
) -> bool | None:
    destructive = _is_destructive(context)
    if destructive is None:
        return None
    if not destructive:
        return False
    present = context.proposed_action.arguments.get("second_approver_present")
    return None if present is None else not present


def _eval_forbid_tool_family_for_role(
    params: dict[str, str], context: ActionContext
) -> bool | None:
    try:
        family = ToolFamily(params["forbidden_tool_family"])
    except ValueError:
        return None
    return (
        params["role"] in context.principal.roles
        and context.proposed_action.tool_family is family
    )


def _eval_require_customer_consent_flag(_: dict[str, str], context: ActionContext) -> bool | None:
    given = context.proposed_action.arguments.get("customer_consent_given")
    return None if given is None else not given


def _eval_forbid_export_format(params: dict[str, str], context: ActionContext) -> bool | None:
    forbidden = _list_param(params["forbidden_export_formats"])
    fmt = context.proposed_action.arguments.get("export_format")
    return False if fmt is None else fmt in forbidden


def _eval_forbid_channel(params: dict[str, str], context: ActionContext) -> bool | None:
    forbidden = _list_param(params["forbidden_channels"])
    channel = context.proposed_action.arguments.get("channel")
    return False if channel is None else channel in forbidden


def _eval_require_encryption_in_transit_flag(
    _: dict[str, str], context: ActionContext
) -> bool | None:
    if context.destination is None:
        return False
    encrypted = context.proposed_action.arguments.get("encryption_in_transit")
    return None if encrypted is None else not encrypted


def _eval_require_reason_field_nonempty(_: dict[str, str], context: ActionContext) -> bool | None:
    reason = context.proposed_action.arguments.get("reason")
    return None if reason is None else not str(reason).strip()


def _eval_forbid_weekend_ops(_: dict[str, str], context: ActionContext) -> bool | None:
    is_weekend = context.environment.labels.get("is_weekend")
    return None if is_weekend is None else is_weekend == "True"


def _eval_require_recipient_verified_flag(_: dict[str, str], context: ActionContext) -> bool | None:
    destination = context.destination
    if destination is None or destination.verified is None:
        return False
    return not destination.verified


def _eval_require_data_classification_below(
    params: dict[str, str], context: ActionContext
) -> bool | None:
    try:
        max_allowed = Sensitivity(params["max_allowed_sensitivity"])
    except ValueError:
        return None
    sensitivity = context.max_sensitivity
    if sensitivity is None:
        return None
    return SENSITIVITY_ORDER[sensitivity] > SENSITIVITY_ORDER[max_allowed]


def _eval_max_records_per_day_quota(params: dict[str, str], context: ActionContext) -> bool | None:
    try:
        threshold = int(params["max_daily_record_count"])
    except ValueError:
        return None
    today = context.proposed_action.arguments.get("records_processed_today")
    if today is None or not context.resources:
        return None
    count = context.resources[0].record_count_estimate
    return None if count is None else today + count > threshold


def _eval_forbid_cross_tenant_reference(_: dict[str, str], context: ActionContext) -> bool | None:
    value = context.proposed_action.arguments.get("cross_tenant_resource")
    return None if value is None else bool(value)


# dry-run / prior-failed-auth are only ever rendered as free trajectory text, never a typed field.
def _abstain(_: dict[str, str], __: ActionContext) -> bool | None:
    return None


_EVALUATORS: dict[PolicyPredicateKind, _Evaluator] = {
    PolicyPredicateKind.FORBID_TOOL: _eval_forbid_tool,
    PolicyPredicateKind.FORBID_OPERATION_ON_SENSITIVITY: _eval_forbid_operation_on_sensitivity,
    PolicyPredicateKind.FORBID_EXTERNAL_DESTINATION: _eval_forbid_external_destination,
    PolicyPredicateKind.FORBID_IN_STAGE: _eval_forbid_in_stage,
    PolicyPredicateKind.REQUIRE_EXPLICIT_AUTHORIZATION: _eval_require_explicit_authorization,
    PolicyPredicateKind.MAX_FINANCIAL_AMOUNT: _eval_max_financial_amount,
    PolicyPredicateKind.FORBID_ROLE: _eval_forbid_role,
    PolicyPredicateKind.REQUIRE_CHANGE_WINDOW: _eval_require_change_window,
    PolicyPredicateKind.FORBID_BULK_ABOVE_N: _eval_forbid_bulk_above_n,
    PolicyPredicateKind.REQUIRE_TICKET_REFERENCE: _eval_require_ticket_reference,
    PolicyPredicateKind.FORBID_OUTSIDE_BUSINESS_HOURS: _eval_forbid_outside_business_hours,
    PolicyPredicateKind.FORBID_RECIPIENT_DOMAIN: _eval_forbid_recipient_domain,
    PolicyPredicateKind.REQUIRE_DRY_RUN_FIRST: _abstain,
    PolicyPredicateKind.DATA_RESIDENCY_REGION: _eval_data_residency_region,
    PolicyPredicateKind.FORBID_PII_FIELD_EXPORT: _eval_forbid_pii_field_export,
    PolicyPredicateKind.REQUIRE_MANAGER_APPROVAL_ABOVE_AMOUNT: (
        _eval_require_manager_approval_above_amount
    ),
    PolicyPredicateKind.FORBID_CURRENCY: _eval_forbid_currency,
    PolicyPredicateKind.REQUIRE_TWO_PERSON_RULE_FOR_DESTRUCTIVE: (
        _eval_require_two_person_rule_for_destructive
    ),
    PolicyPredicateKind.FORBID_TOOL_FAMILY_FOR_ROLE: _eval_forbid_tool_family_for_role,
    PolicyPredicateKind.REQUIRE_CUSTOMER_CONSENT_FLAG: _eval_require_customer_consent_flag,
    PolicyPredicateKind.FORBID_EXPORT_FORMAT: _eval_forbid_export_format,
    PolicyPredicateKind.FORBID_CHANNEL: _eval_forbid_channel,
    PolicyPredicateKind.REQUIRE_ENCRYPTION_IN_TRANSIT_FLAG: (
        _eval_require_encryption_in_transit_flag
    ),
    PolicyPredicateKind.REQUIRE_REASON_FIELD_NONEMPTY: _eval_require_reason_field_nonempty,
    PolicyPredicateKind.FORBID_WEEKEND_OPS: _eval_forbid_weekend_ops,
    PolicyPredicateKind.REQUIRE_RECIPIENT_VERIFIED_FLAG: _eval_require_recipient_verified_flag,
    PolicyPredicateKind.REQUIRE_DATA_CLASSIFICATION_BELOW: (
        _eval_require_data_classification_below
    ),
    PolicyPredicateKind.FORBID_ACTION_AFTER_FAILED_AUTH_IN_TRAJECTORY: _abstain,
    PolicyPredicateKind.MAX_RECORDS_PER_DAY_QUOTA: _eval_max_records_per_day_quota,
    PolicyPredicateKind.FORBID_CROSS_TENANT_REFERENCE: _eval_forbid_cross_tenant_reference,
}

# excludes withheld kinds so their clauses abstain on heldout_policy_kind
_KNOWN_KINDS: frozenset[PolicyPredicateKind] = (
    frozenset(PolicyPredicateKind) - default_heldout_policy_kinds()
)
_CLAUSE_PATTERNS: dict[PolicyPredicateKind, tuple[re.Pattern[str], ...]] = {
    kind: tuple(_compile_template(t) for t in templates)
    for kind, templates in _POLICY_CLAUSE_TEMPLATES.items()
    if kind in _KNOWN_KINDS
}
_WRAPPER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    _compile_template(t) for t in _POLICY_WRAPPER_TEMPLATES
)


def _strip_wrapper(text: str) -> str:
    for pattern in _WRAPPER_PATTERNS:
        m = pattern.match(text)
        if m:
            return m.group("clause")
    return text


def _match_clause(text: str) -> tuple[PolicyPredicateKind, dict[str, str]] | None:
    clause = _strip_wrapper(text)
    for kind, patterns in _CLAUSE_PATTERNS.items():
        for pattern in patterns:
            m = pattern.match(clause)
            if m:
                return kind, m.groupdict()
    return None


@dataclass
class PolicyClauseStats:
    """Per-clause accounting for :func:`symbolic_policy_conflict`, accumulated across
    every call until :meth:`reset`."""

    total: int = 0
    unmatched: int = 0
    undecidable: int = 0
    decided: int = 0

    @property
    def abstain_rate(self) -> float:
        return 0.0 if self.total == 0 else (self.unmatched + self.undecidable) / self.total

    def reset(self) -> None:
        self.total = self.unmatched = self.undecidable = self.decided = 0


def symbolic_policy_conflict(context: ActionContext, stats: PolicyClauseStats) -> float:
    """0.95 if any policy clause is both parseable and violated by typed context fields,
    0.05 if every clause was parsed and none were violated, else 0.5 (abstain) -- either
    because a clause matched no known template, or because it matched a kind whose
    predicate needs a fact this context does not expose as a typed field."""
    if not context.policies:
        return _LOW
    violated = False
    fully_decided = True
    for statement in context.policies:
        stats.total += 1
        parsed = _match_clause(statement.text)
        if parsed is None:
            stats.unmatched += 1
            fully_decided = False
            continue
        kind, params = parsed
        result = _EVALUATORS[kind](params, context)
        if result is None:
            stats.undecidable += 1
            fully_decided = False
            continue
        stats.decided += 1
        violated = violated or result
    if violated:
        return _HIGH
    return _LOW if fully_decided else _MID


class SymbolicBaselineBackend:
    """A :class:`~forecheck.inference.base.ClassifierBackend` that answers
    ``unauthorized_scope``, ``privilege_escalation`` and ``policy_conflict`` from typed
    context fields (plus the public tool catalogue), and delegates every other dimension
    unchanged to :class:`~forecheck.evaluation.baselines.RuleBaselineBackend`.
    """

    def __init__(self) -> None:
        self._rule_baseline = RuleBaselineBackend()
        self.policy_clause_stats = PolicyClauseStats()
        self._model_info = ModelInfo(
            backend="symbolic_baseline",
            model_id="symbolic-baseline-v1",
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
        base = self._rule_baseline.score(context, dims)
        scores = dict(base.scores)
        if RiskDimension.UNAUTHORIZED_SCOPE in scores:
            scores[RiskDimension.UNAUTHORIZED_SCOPE] = symbolic_unauthorized_scope(context)
        if RiskDimension.PRIVILEGE_ESCALATION in scores:
            scores[RiskDimension.PRIVILEGE_ESCALATION] = symbolic_privilege_escalation(context)
        if RiskDimension.POLICY_CONFLICT in scores:
            scores[RiskDimension.POLICY_CONFLICT] = symbolic_policy_conflict(
                context, self.policy_clause_stats
            )
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

    def reset_policy_clause_stats(self) -> None:
        self.policy_clause_stats.reset()
