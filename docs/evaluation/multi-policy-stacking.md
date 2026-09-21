# Multi-policy stacking evaluation

Guardrail buyers commonly deploy several independently-tuned binary guards at once and
alert whenever any one fires. Each guard's own false-positive rate compounds under that
OR, so the stack becomes more conservative purely from adding guards, not from any guard
getting worse. forecheck's design is different: one calibrated probability vector feeds
one deterministic policy engine with a single combination rule applied once. This
metric measures that difference directly, on the same probability vectors and the same
rules, rather than arguing about it in the abstract.

Implementation: `src/forecheck/evaluation/stacking.py`. Wired into
`forecheck evaluate --stacking-bundles <names/paths> --stacking-synthetic`, and rendered
in `report.md` under "Multi-policy stacking" when either flag is used.

All numbers this metric produces are synthetic, per `docs/evaluation-plan.md` §1.

## 1. The three strategies

For k = 1..K policies (a policy is a `PolicyBundle`), three decisions are computed per
example:

* **independent**: each of the first k policies is evaluated on its own, and the
  stack's decision is the most severe of the k individual decisions
  (`combine_matched_rules` applied to a synthetic match per policy, one per its own
  final decision). This is "OR N independent guards".
* **joint**: the first k policies' rules are merged by rule id into one bundle
  (`merge_bundles`) and evaluated once, in `decision_mode: threshold`. Every rule that
  could fire, fires against the same combination pass, so the engine's own
  most-restrictive-wins / `hard` / `allow_override` semantics apply across the whole
  rule set, not within each policy in isolation.
* **expected_cost_joint**: the same merged bundle, evaluated in `decision_mode:
  expected_cost` (`docs/policy-dsl.md`) instead of `threshold`. The argmin uses every
  covered dimension's probability jointly, so a single miscalibrated dimension can be
  outweighed by the other covered dimensions' low, correctly-benign probabilities
  rather than triggering the stack on its own. A fired `hard` rule still forces DENY.

`--stacking-synthetic` builds 11 single-dimension policies, one per `RiskDimension`:
DENY when `p(dimension) >= tau`, with `tau` taken from the F1-optimal threshold on the
threshold-selection split when one was supplied to `forecheck evaluate`, else 0.5.
`insufficient_context` routes to REVIEW rather than DENY, since it is not derivable from
the latent scenario alone (`contracts.enums.META_DIMENSIONS`). `--stacking-bundles`
names real shipped or custom bundles (e.g. `conservative,balanced`); both flags combine,
appending the synthetic policies after the named bundles.

## 2. What "over-conservative" means numerically

For each (k, strategy) the report gives:

* **false_positive_rate**: among covered-benign examples (all dimensions the first k
  policies reference are `NO`/`NOT_APPLICABLE`), the fraction the stack decided
  anything other than `ALLOW`. Rising `fpr(k)` under `independent` at fixed rules is
  exactly the compounding effect: stacking more guards flags more benign traffic.
* **false_negative_rate**: among covered-risky examples (any covered dimension is
  `YES`), the fraction the stack still `ALLOW`ed.
* **review_rate**: fraction of all examples decided `REVIEW`.
* **mean_risk_weighted_cost**: `decisions.decision_metrics`'s existing cost weights
  (`CostMatrix`), applied to the stack's decisions.

## 3. How to read the table

Compare the `independent` and `joint` rows at the same k. When the input policies use
only plain, non-hard, non-override rules, as `--stacking-synthetic`'s policies do,
the two strategies are mathematically identical at every k: `combine_matched_rules`
reduces to "most severe fired rule wins", and that reduction does not care how the fired
rules were partitioned across bundles before being pooled. `fpr_independent(k)` still
rises with k in that case (`tests/evaluation/test_stacking.py::test_independent_stack_false_positive_rate_grows_monotonically_with_k`),
demonstrating the OR-compounding effect on its own; `joint` tracks it exactly rather
than improving on it, because there is nothing in a plain threshold rule set for the
engine's combination logic to do differently.

The two strategies diverge once real bundles with `hard` and `allow_override` rules are
stacked (`--stacking-bundles conservative,balanced`, or any custom bundle with an
`allow_override` carve-out like `balanced.yaml`'s `allow_reversible_dev_action`): an
`allow_override` rule that fires in one input policy can only escape that policy's own
non-hard restrictive rules under `independent`, but under `joint` it is pooled with
every other input policy's fired rules and can also escape a non-hard `DENY`/`REVIEW`
rule that fired in a *different* policy: see
`test_joint_can_be_strictly_less_restrictive_when_an_override_fires_across_policies` for
a constructed example. This is a direct, existing consequence of
`policies.engine.combine_matched_rules`, not special-cased in `stacking.py`.

The property this module guarantees is therefore: **joint's FPR is never worse than
independent's for rule sets with no cross-policy hard-vs-override interaction, and can
be strictly better once real bundles are mixed in.** A universal "joint <= independent
for any rule set" claim is not made and is not true in general: a `hard` rule firing in
one policy can block an `allow_override` that fired in another, and whether that nets
out above or below the independent stack's own severity depends on the specific rules
in play. Read the independent row as the compounding baseline and the joint row as what
forecheck's actual combination logic does instead, not as an unconditionally lower
bound.

## 4. What expected_cost_joint changes

`joint` above only changes *which rules get pooled*; it does not change *how* a
decision is reached, so it inherits `independent`'s compounding on plain threshold
rule sets. `expected_cost_joint` changes the decision rule itself.
`test_expected_cost_joint_fpr_bounded_while_independent_fpr_grows_with_k`
(`tests/evaluation/test_stacking.py`) constructs six benign examples, each with its
own dimension spiked to p=0.9 and every other covered dimension at a correctly-benign
baseline p=0.2, all rules given a symmetric cost block
(`allow_if_risky == deny_if_benign == 1.0`, `review = 0.5`). `independent`'s and
`joint`'s false-positive rate is identical at every k (both reduce to "most severe
fired rule wins") and reaches 1.0 by k=6:

| k | independent / joint fpr | expected_cost_joint fpr |
|---|---|---|
| 1 | 0.167 | 0.167 |
| 2 | 0.333 | 0.333 |
| 3 | 0.500 | 0.000 |
| 4 | 0.667 | 0.000 |
| 5 | 0.833 | 0.000 |
| 6 | 1.000 | 0.000 |

At k <= 2, each flagged example's own spike is still the dominant signal for both
strategies. At k >= 3, `expected_cost_joint`'s aggregate over the growing set of
low-probability covered dimensions outweighs the single spike, and the decision
flips back to ALLOW; `independent` has no such correction, since OR-ing per-rule
decisions can only add more ways to fire, never fewer.
`test_expected_cost_joint_fnr_not_worse_than_independent_at_k1` checks the other
direction: on a genuinely risky example at k=1, `expected_cost_joint`'s false-negative
rate is no worse than `independent`'s (both 0.0 here; a symmetric-cost, high-probability
positive is cheap to deny under either rule).
