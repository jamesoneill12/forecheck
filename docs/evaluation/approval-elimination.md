# Approval-elimination metric

The headline product metric (`docs/product-spec.md` §1) is not an accuracy number: it
is *how many human approvals a deployment can remove at a fixed, chosen incident rate*.
This document defines that metric precisely, maps it onto quantities the evaluation
suite already computes, and specifies — without building it — what
`forecheck evaluate --approval-curve` would print.

All numbers this metric would currently produce are synthetic, per
`docs/evaluation-plan.md` §1. Nothing here is a real-world approval-reduction claim
until a class-3 (human-labelled or real-traffic) evaluation exists.

## 1. Definitions

**Baseline population.** The set of actions that a policy bundle's non-abstaining
rules would route to `REVIEW` absent any calibration-confidence gating — i.e. every
action a deployment currently sends to a human today. This is the denominator for
approval elimination.

**Approvals eliminated.** At a chosen abstention/confidence threshold, the fraction of
the baseline `REVIEW` population that forecheck instead auto-decides as `ALLOW` or
`DENY`:

```
approvals_eliminated = |{a in baseline_review : decision(a) != REVIEW}| / |baseline_review|
```

This is a coverage quantity: it is exactly "1 − review rate", scoped to the population
that would otherwise require a human.

**Covered dimensions.** The subset of the eleven risk dimensions whose `YES` label
makes an auto-`ALLOW` an incident. Default is
`evaluation.decisions.HIGH_SEVERITY_DIMENSIONS` (`destructive_or_irreversible_action`,
`privilege_escalation`, `sensitive_data_exposure`, `financial_commitment`,
`unauthorized_scope`) — the same set `decision_metrics` already uses for false-allow
rate. A deployment may narrow or widen this set; the curve must state which set it used.

**Incident rate.** Among the actions forecheck auto-`ALLOW`ed (never among auto-`DENY`,
which by definition did not proceed), the fraction whose ground truth — or, once it
exists, human feedback via `POST /v1/feedback` — carries `YES` on any covered
dimension:

```
incident_rate = |{a in auto_allow : any(label[d] == YES for d in covered_dims)}| / |auto_allow|
```

**The curve.** Sweep the confidence/abstention threshold from most to least
conservative. At each point, plot `(approvals_eliminated, incident_rate)`. This is a
risk-coverage curve in decision space rather than label space: coverage is "how much of
the review queue we removed", risk is "how often the removed-and-auto-allowed slice was
wrong". A useful deployment finds a threshold with high elimination and an incident rate
at or below whatever rate humans themselves produce today.

## 2. Mapping onto existing selective-risk quantities

`evaluation/selective.py` already computes exactly this shape of curve one level down,
for a single dimension's binary prediction:

| Approval-elimination quantity | Existing selective-risk quantity |
|---|---|
| Abstention/confidence threshold sweep | `confidence` array + `threshold` in `selective_risk_coverage` |
| Approvals eliminated | `coverage` (`ranks / n`), restricted to the baseline-review population |
| Incident rate | `risk` (`cum_errors / ranks`), restricted to the `decision == ALLOW` subset and redefined as "any covered-dimension positive", not generic prediction error |
| The curve's summary number | `aurc` — call the approval-elimination analogue `AUEC` (area under the elimination curve) to avoid conflating it with per-dimension AURC |
| Fixed operating points | `selective_accuracy_at_coverage`, restated as `incident_rate_at_elimination` for `{50, 70, 80, 90, 100}%` |

The one real difference: `selective_risk_coverage`'s risk is "prediction wrong on the
kept subset" for one dimension; the approval-elimination curve's risk is "auto-allowed
and later found risky on any covered dimension", which only makes sense conditioned on
`decision == ALLOW`, not on the full kept-by-confidence subset (an auto-`DENY` carries no
incident risk because the action never ran). A direct reuse of
`selective_risk_coverage` would need that conditioning added — it is not a drop-in call.

`decisions.decision_metrics` already computes `review_rate` and `false_allow_rate` for
one fixed policy bundle and one fixed set of thresholds; approval elimination is what
you get by computing `decision_metrics` repeatedly across a threshold sweep and plotting
`1 - review_rate` against a false-allow rate restricted to the covered dimensions, so no
new ground-truth logic is needed — only the sweep and the curve assembly.

## 3. What `forecheck evaluate --approval-curve` would print

Not built. `src/forecheck/cli_cmds/evaluate.py` is under active concurrent edit in this
branch, so this section specifies the contract for whoever wires it in rather than
adding the flag here.

For a stated policy bundle, split, and covered-dimension set, sweeping the confidence
threshold over (e.g.) 20 points:

```
approval_curve:
  bundle: balanced
  split: test
  covered_dimensions: [destructive_or_irreversible_action, privilege_escalation,
                        sensitive_data_exposure, financial_commitment, unauthorized_scope]
  baseline_review_n: <n>
  points:
    - threshold: <float>
      approvals_eliminated: <float 0..1>
      incident_rate: <float 0..1, or null if auto_allow_n == 0>
      auto_allow_n: <int>
      auto_deny_n: <int>
      still_review_n: <int>
  auec: <float>
  incident_rate_at_elimination: {0.5: <float|null>, 0.7: ..., 0.8: ..., 0.9: ..., 1.0: ...}
  evaluation_class: <as in evaluation-plan.md §1; synthetic until class 3 exists>
```

Every headline point would carry a bootstrap CI per `evaluation-plan.md` §3.10, and the
report would print the fixed "synthetic data, no real-world safety claim" line for
classes 1 and 2, matching every other report in this suite.

## 4. Implemented shape (`src/forecheck/evaluation/approval_curve.py`)

The curve above (§1-3) is specified as a threshold sweep restricted to the baseline
`REVIEW` population, with the threshold left an open question (§5's first item). What
is actually implemented is a related but narrower construction, chosen to be
computable purely from scores the evaluation runner already has, with no new
ground-truth or calibration-confidence machinery:

* **Score.** Per example, `expected_costs(bundle, response).allow`
  (`forecheck.policies.engine.expected_costs`) — the same "expected cost of ALLOW"
  quantity `decision_mode: expected_cost` computes over the bundle's covered
  dimensions (`docs/policy-dsl.md` §2.3), regardless of the bundle's own
  `decision_mode`. This is the expected-cost formulation named in the task that added
  this section; the max-calibrated-probability alternative was not implemented.
* **Ground truth.** An example is "risky" if any dimension the bundle's rules
  reference via a `score` leaf (`bundle_covered_dimensions`) carries a `YES` label.
* **Population.** All examples in the evaluated split — not the doc's "baseline
  `REVIEW` absent calibration-confidence gating" population, which would need a
  counterfactual re-evaluation this layer does not have. This is a simplification, not
  an equivalence.
* **Curve and operating points.** Sort examples ascending by score. For allow-set size
  `k`, `incident_rate(k)` is the fraction of the `k` lowest-score examples that are
  risky; `allow_fraction(k) = k / n`. The curve is one `(allow_fraction, incident_rate)`
  point per `k = 1..n`. For each budget `b`, the operating point takes the largest `k`
  with `incident_rate(k) <= b` (0 if none exists) as `approvals_eliminated`; examples
  outside that allow-set keep the bundle's own `DENY` decision (`engine.evaluate`),
  and everything else counts as `review_fraction`.
* **Not implemented from §3's contract:** `AUEC`, bootstrap CIs on curve points, and
  the `evaluation_class` synthetic-disclaimer line (the caller's `EvaluationReport`
  already carries and prints that disclaimer once for the whole report).

### How to run

```
forecheck evaluate --run <run-dir> --split <split> --class <evaluation_class> --approval-curve balanced
```

`--approval-curve` accepts a built-in bundle name (`balanced`, `conservative`,
`permissive`, ...) or a path to a bundle YAML; it is independent of `--bundle`
(the bundle used for `decisions`/`stacking`) and off by default. The result is
written to `report.json` under `approval_elimination` and rendered as an "Approval
elimination" section in `report.md`. It is pure post-processing over scores the run
already computed, so it is cheap to add to an existing `forecheck evaluate` command.

## 5. Open questions (left as TODO, not blocking)

- Whether "the abstention threshold" sweeps the calibrator's predictive-interval width,
  the per-response `abstain_below_confidence` option, or a synthetic re-parametrization
  of each bundle's `REVIEW` rule thresholds. The three are not equivalent and the
  eventual implementation must pick one and say so in the report.
- Whether incident rate should be measured against dataset ground truth (class 1/2,
  available now) or against `POST /v1/feedback` outcomes (class 3, available once the
  flywheel has traffic) — likely both, reported separately and never averaged.
