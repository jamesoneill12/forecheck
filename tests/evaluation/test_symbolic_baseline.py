from __future__ import annotations

from conftest import make_example

from forecheck.contracts import (
    AgentIdentity,
    FinancialExposure,
    PolicyStatement,
    Principal,
    ProposedAction,
    RiskDimension,
)
from forecheck.data.rendering import _POLICY_CLAUSE_TEMPLATES, _POLICY_WRAPPER_TEMPLATES
from forecheck.data.splitting import default_heldout_policy_kinds
from forecheck.evaluation.baselines import RuleBaselineBackend
from forecheck.evaluation.symbolic_baseline import (
    PolicyClauseStats,
    SymbolicBaselineBackend,
    symbolic_policy_conflict,
    symbolic_privilege_escalation,
    symbolic_unauthorized_scope,
)


def _with_scopes(context, *, entitlements: list[str], delegated_scopes: list[str]):
    return context.model_copy(
        update={
            "principal": Principal(id="user-1", entitlements=entitlements),
            "agent": AgentIdentity(id="agent-1", delegated_scopes=delegated_scopes),
        }
    )


def test_symbolic_baseline_model_info_backend_name() -> None:
    assert SymbolicBaselineBackend().model_info.backend == "symbolic_baseline"


def test_symbolic_baseline_delegates_other_dimensions_to_rule_baseline() -> None:
    example = make_example("e")
    symbolic = SymbolicBaselineBackend().score(example.context)
    rule = RuleBaselineBackend().score(example.context)
    for dimension in RiskDimension:
        if dimension in (
            RiskDimension.UNAUTHORIZED_SCOPE,
            RiskDimension.PRIVILEGE_ESCALATION,
            RiskDimension.POLICY_CONFLICT,
        ):
            continue
        assert symbolic.scores[dimension] == rule.scores[dimension]


def test_unauthorized_scope_low_when_required_scope_is_covered() -> None:
    example = make_example("e", tool_name="email.send_message")
    context = _with_scopes(
        example.context, entitlements=["email.send"], delegated_scopes=["email.send"]
    )
    assert symbolic_unauthorized_scope(context) == 0.05


def test_unauthorized_scope_high_when_entitlement_missing() -> None:
    example = make_example("e", tool_name="email.send_message")
    context = _with_scopes(example.context, entitlements=[], delegated_scopes=["email.send"])
    assert symbolic_unauthorized_scope(context) == 0.95


def test_unauthorized_scope_high_when_delegated_scope_missing() -> None:
    example = make_example("e", tool_name="email.send_message")
    context = _with_scopes(example.context, entitlements=["email.send"], delegated_scopes=[])
    assert symbolic_unauthorized_scope(context) == 0.95


def test_unauthorized_scope_abstains_on_unknown_tool() -> None:
    example = make_example("e", tool_name="nonexistent.tool")
    context = example.context.model_copy(
        update={"proposed_action": ProposedAction(tool_name="nonexistent.tool")}
    )
    assert symbolic_unauthorized_scope(context) == 0.5


def test_privilege_escalation_high_when_authority_widens() -> None:
    example = make_example("e", tool_name="cloud.create_iam_role")
    proposed_action = ProposedAction(
        tool_name="cloud.create_iam_role",
        arguments={
            "authority_before": ["iam.write"],
            "authority_after": ["iam.write", "authority:elevated"],
        },
    )
    context = example.context.model_copy(update={"proposed_action": proposed_action})
    assert symbolic_privilege_escalation(context) == 0.95


def test_privilege_escalation_low_when_authority_unchanged() -> None:
    example = make_example("e", tool_name="cloud.create_iam_role")
    proposed_action = ProposedAction(
        tool_name="cloud.create_iam_role",
        arguments={"authority_before": ["iam.write"], "authority_after": ["iam.write"]},
    )
    context = example.context.model_copy(update={"proposed_action": proposed_action})
    assert symbolic_privilege_escalation(context) == 0.05


def test_privilege_escalation_low_when_tool_never_touches_authority() -> None:
    example = make_example("e", tool_name="email.send_message")
    assert symbolic_privilege_escalation(example.context) == 0.05


def test_policy_conflict_low_when_no_policies() -> None:
    example = make_example("e", policies=())
    assert symbolic_policy_conflict(example.context, PolicyClauseStats()) == 0.05


def test_policy_conflict_high_when_clause_is_violated() -> None:
    statement = PolicyStatement(
        id="p0", text="Policy: financial commitments above 100.0 are forbidden without approval."
    )
    example = make_example("e", policies=[statement])
    context = example.context.model_copy(update={"financial": FinancialExposure(amount=500.0)})
    stats = PolicyClauseStats()
    assert symbolic_policy_conflict(context, stats) == 0.95
    assert stats.decided == 1
    assert stats.abstain_rate == 0.0


def test_policy_conflict_low_when_clause_is_satisfied() -> None:
    statement = PolicyStatement(
        id="p0", text="Policy: financial commitments above 100.0 are forbidden without approval."
    )
    example = make_example("e", policies=[statement])
    context = example.context.model_copy(update={"financial": FinancialExposure(amount=50.0)})
    assert symbolic_policy_conflict(context, PolicyClauseStats()) == 0.05


def test_policy_conflict_abstains_on_unrecognized_clause_text() -> None:
    statement = PolicyStatement(id="p0", text="This sentence matches no known template at all.")
    example = make_example("e", policies=[statement])
    stats = PolicyClauseStats()
    assert symbolic_policy_conflict(example.context, stats) == 0.5
    assert stats.unmatched == 1
    assert stats.abstain_rate == 1.0


def test_policy_conflict_abstains_on_heldout_kind_clause() -> None:
    heldout_kind = next(iter(default_heldout_policy_kinds()))
    template = _POLICY_CLAUSE_TEMPLATES[heldout_kind][0]
    clause = template.format(
        tool_name="named",
        op="read",
        sensitivity="confidential",
        stage="production",
        amount=100,
        role="restricted",
        max_record_count=10,
        business_hour_start=9,
        business_hour_end=17,
        allowed_domains="corp-internal.example",
        allowed_regions="us-east-1",
        pii_fields="ssn",
        forbidden_currencies="USD",
        forbidden_tool_family="email_messaging",
        forbidden_export_formats="csv",
        forbidden_channels="email",
        max_allowed_sensitivity="confidential",
        max_daily_record_count=100,
    )
    text = _POLICY_WRAPPER_TEMPLATES[0].format(clause=clause)
    statement = PolicyStatement(id="p0", text=text)
    example = make_example("e", policies=[statement])
    stats = PolicyClauseStats()
    assert symbolic_policy_conflict(example.context, stats) == 0.5
    assert stats.unmatched == 1
