from __future__ import annotations

from itertools import pairwise

from conftest import all_no_labels, make_example

from forecheck.contracts import (
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    Decision,
    DimensionScore,
    LabelValue,
    ModelInfo,
    RiskDimension,
    TruncationInfo,
)
from forecheck.evaluation.stacking import (
    merge_bundles,
    stacking_report,
    synthetic_dimension_policies,
)
from forecheck.policies.dsl import Condition, PolicyBundle, Rule, RuleKind, UnknownAs

MODEL_INFO = ModelInfo(
    backend="stub", model_id="stub-v1", prompt_contract_hash="n/a", label_schema_version="1.0"
)
CALIBRATION_INFO = CalibrationInfo(method=CalibrationMethod.TEMPERATURE)

DIMS = list(RiskDimension)


def _response(probabilities: dict[RiskDimension, float], default: float = 0.1) -> ClassifyResponse:
    scores = [
        DimensionScore(dimension=d, probability=probabilities.get(d, default), calibrated=True)
        for d in DIMS
    ]
    return ClassifyResponse(
        scores=scores,
        model=MODEL_INFO,
        calibration=CALIBRATION_INFO,
        truncation=TruncationInfo(),
        latency_ms=1.0,
    )


def _spiky_examples_and_responses(n: int) -> tuple[list, list[ClassifyResponse]]:
    """n benign examples; example i's only elevated score is on dimension i.

    Stacking the first k synthetic dimension-policies (k <= n) therefore flags
    exactly examples 0..k-1, and leaves the rest untouched.
    """
    examples = [make_example(f"benign-{i}", family_id=f"fam-{i}") for i in range(n)]
    responses = [_response({DIMS[i]: 0.9}) for i in range(n)]
    return examples, responses


def test_independent_stack_false_positive_rate_grows_monotonically_with_k() -> None:
    n = 6
    examples, responses = _spiky_examples_and_responses(n)
    policies = synthetic_dimension_policies()[:n]

    report = stacking_report(examples, responses, policies)
    independent_rows = sorted(
        (row for row in report.rows if row.strategy == "independent"), key=lambda r: r.k
    )

    fprs = [row.false_positive_rate for row in independent_rows]
    assert fprs == [k / n for k in range(1, n + 1)]
    assert all(a <= b for a, b in pairwise(fprs))
    assert fprs[0] < fprs[-1]


def test_joint_equals_independent_for_plain_threshold_policies() -> None:
    """No rule in ``synthetic_dimension_policies`` is hard or allow_override, so
    ``combine_matched_rules`` reduces to "most severe fired rule wins" for both
    strategies. Merging rule sets before combining (joint) or combining each
    bundle's own rules and then OR-ing the finals (independent) then agree exactly,
    at every k: joint FPR == independent FPR <= independent FPR trivially holds as
    equality, not just inequality, in this rule shape.
    """
    n = 5
    examples, responses = _spiky_examples_and_responses(n)
    policies = synthetic_dimension_policies()[:n]

    report = stacking_report(examples, responses, policies)
    by_k: dict[int, dict[str, float | None]] = {}
    for row in report.rows:
        by_k.setdefault(row.k, {})[row.strategy] = row.false_positive_rate

    for k, rates in by_k.items():
        assert rates["joint"] == rates["independent"], k
        assert rates["joint"] <= rates["independent"]


def _bundle(
    bundle_id: str, rule: Rule, *, default_decision: Decision = Decision.ALLOW
) -> PolicyBundle:
    return PolicyBundle(
        bundle_id=bundle_id,
        version=1,
        dsl_version="1.0",
        description="test bundle",
        default_decision=default_decision,
        uncalibrated_decision=Decision.REVIEW,
        allow_uncalibrated=True,
        unknown_as=UnknownAs.WORST_CASE,
        rules=[rule],
    )


def test_joint_can_be_strictly_less_restrictive_when_an_override_fires_across_policies() -> None:
    """An allow_override rule only escapes the decision within its own bundle under
    independent stacking, since each bundle is evaluated and combined on its own
    before the OR. Under joint stacking, all rules are pooled into one combination
    pass, so the same override can also absorb a non-hard deny rule that fired in a
    *different* input policy. This is a direct consequence of
    ``combine_matched_rules``'s existing semantics, not a special case coded here.
    """
    override_rule = Rule(
        id="override_dev_reversible",
        description="reversible dev action allows freely",
        decision=Decision.ALLOW,
        kind=RuleKind.ALLOW_OVERRIDE,
        when=Condition(score=RiskDimension.POLICY_CONFLICT, lt=0.05),
        obligations=["log_to_audit_sink"],
    )
    review_rule = Rule(
        id="review_something",
        description="review signal in the override bundle",
        decision=Decision.REVIEW,
        when=Condition(score=RiskDimension.INSUFFICIENT_CONTEXT, gte=0.5),
    )
    bundle_with_override = _bundle(
        "has-override",
        review_rule,
        default_decision=Decision.ALLOW,
    )
    bundle_with_override = bundle_with_override.model_copy(
        update={"rules": [review_rule, override_rule]}
    )
    deny_rule = Rule(
        id="deny_something",
        description="unrelated non-hard deny",
        decision=Decision.DENY,
        hard=False,
        when=Condition(score=RiskDimension.FINANCIAL_COMMITMENT, gte=0.5),
    )
    bundle_with_deny = _bundle("has-deny", deny_rule)

    example = make_example("mixed")
    response = _response(
        {
            RiskDimension.INSUFFICIENT_CONTEXT: 0.9,
            RiskDimension.POLICY_CONFLICT: 0.01,
            RiskDimension.FINANCIAL_COMMITMENT: 0.9,
        }
    )

    report = stacking_report([example], [response], [bundle_with_override, bundle_with_deny])
    row_by_strategy = {row.strategy: row for row in report.rows if row.k == 2}

    assert row_by_strategy["independent"].false_positive_rate == 1.0
    assert row_by_strategy["joint"].false_positive_rate == 0.0
    assert (
        row_by_strategy["joint"].false_positive_rate
        <= row_by_strategy["independent"].false_positive_rate
    )


def test_meta_dimension_synthetic_policy_reviews_instead_of_denying() -> None:
    policies = synthetic_dimension_policies()
    insufficient_context_policy = next(
        p for p in policies if p.bundle_id == "synthetic-insufficient_context"
    )
    assert insufficient_context_policy.rules[0].decision is Decision.REVIEW


def test_merge_bundles_deduplicates_by_rule_id() -> None:
    rule = Rule(
        id="shared",
        description="shared rule",
        decision=Decision.DENY,
        when=Condition(score=RiskDimension.FINANCIAL_COMMITMENT, gte=0.5),
    )
    a = _bundle("a", rule)
    b = _bundle("b", rule)
    merged = merge_bundles([a, b], "merged")
    assert [r.id for r in merged.rules] == ["shared"]


def test_merge_bundles_default_decision_is_most_severe() -> None:
    allow_bundle = _bundle(
        "allow-default",
        Rule(
            id="r1",
            description="r1",
            decision=Decision.DENY,
            when=Condition(score=RiskDimension.FINANCIAL_COMMITMENT, gte=0.9),
        ),
        default_decision=Decision.ALLOW,
    )
    review_bundle = _bundle(
        "review-default",
        Rule(
            id="r2",
            description="r2",
            decision=Decision.DENY,
            when=Condition(score=RiskDimension.FINANCIAL_COMMITMENT, gte=0.9),
        ),
        default_decision=Decision.REVIEW,
    )
    merged = merge_bundles([allow_bundle, review_bundle], "merged")
    assert merged.default_decision is Decision.REVIEW


def test_stacking_report_empty_policies_raises() -> None:
    example = make_example("x")
    response = _response({})
    try:
        stacking_report([example], [response], [])
    except ValueError as exc:
        assert "at least one policy" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_false_negative_rate_counts_missed_covered_positives() -> None:
    risky = make_example(
        "risky",
        labels=all_no_labels(**{RiskDimension.FINANCIAL_COMMITMENT: LabelValue.YES}),
    )
    policies = [synthetic_dimension_policies()[DIMS.index(RiskDimension.FINANCIAL_COMMITMENT)]]
    response = _response({RiskDimension.FINANCIAL_COMMITMENT: 0.1})

    report = stacking_report([risky], [response], policies)
    for row in report.rows:
        assert row.false_negative_rate == 1.0
        assert row.n_covered_risky == 1
