# The policy DSL

A policy bundle is declarative YAML: no embedded code, nothing calls `eval` (ADR
0007). Schema lives in `src/forecheck/policies/dsl.py`; the evaluator is
`src/forecheck/policies/engine.py`.

## 1. Grammar recap

A `Condition` node sets exactly one of `all` / `any` / `not` (combinators) or
`score` / `fact` (leaf predicates). A `score` leaf names a `RiskDimension` and a
threshold (`gte`/`gt`/`lte`/`lt`); a `fact` leaf names a registered context fact and
a comparator (`is`/`in`/`gte`.../`lte`...). A `Rule` pairs a `when` condition with a
`decision`, an optional `hard` flag, an optional `kind: allow_override`, and
`obligations`. A `PolicyBundle` is `bundle_id`, `version`, `dsl_version`,
`default_decision`, `uncalibrated_decision`, `allow_uncalibrated`, `unknown_as` and
`rules`. See `policies/README.md` for the three shipped bundles and the design
choices behind them (fail-closed defaults, no bare `tool_name` denies, ...).

Combination is most-restrictive-wins (`combine_matched_rules`): the most severe
decision among fired rules, unless a non-hard `allow_override` fired and no `hard`
rule also fired, in which case the decision is `ALLOW`. This is `decision_mode:
threshold`, the default.

## 2. Expected-cost decision mode

### 2.1 Why

Under `threshold` mode, stacking several single-dimension policies and OR-ing their
decisions (`independent`) is mathematically identical to merging their rules into
one bundle and evaluating once (`joint`): both reduce to "most severe fired rule
wins" (see `docs/evaluation/multi-policy-stacking.md`). Neither uses the joint
probability vector; each rule only ever looks at its own dimension against its own
threshold. Composing more guards therefore compounds false positives with `k`
regardless of which of the two you pick.

`decision_mode: expected_cost` is a different combination rule, not a different
threshold: it picks whichever of `ALLOW` / `REVIEW` / `DENY` minimises expected cost
over the bundle's covered dimensions' *probabilities*, jointly. A single spiky,
miscalibrated dimension can be outweighed by several other covered dimensions
sitting at a low, correctly-benign probability, once there are enough of them —
composition without the OR's one-guard-fires-everything-loses behaviour.

### 2.2 DSL fields

* `PolicyBundle.decision_mode: threshold | expected_cost` — bundle-level, defaults to
  `threshold`. Fully backwards compatible: omitting it changes nothing.
* `Rule.cost: {allow_if_risky, review, deny_if_benign} | null` — optional, per rule.
  Only consulted when the bundle's `decision_mode` is `expected_cost`. Applies to
  whichever `RiskDimension`(s) that rule's `when` tree references via a `score`
  leaf. When more than one rule in a bundle references the same dimension, the
  first one (in `rules` order) that sets a `cost` wins for that dimension.
  `allow_if_risky` and `deny_if_benign` must be `> 0`; `review` must be `>= 0`.

A rule with no `cost` block falls back to `default_cost_for_dimension` (in
`forecheck.policies.dsl`), a severity-derived default table:

| Tier | Dimensions | allow_if_risky | review | deny_if_benign |
|---|---|---|---|---|
| critical | `destructive_or_irreversible_action`, `sensitive_data_exposure`, `untrusted_destination` | 10.0 | 0.5 | 2.0 |
| high | `privilege_escalation`, `financial_commitment`, `unauthorized_scope` | 5.0 | 0.3 | 1.5 |
| standard | `prompt_injection_influence`, `external_communication`, `policy_conflict`, `suspicious_action_sequence` | 3.0 | 0.2 | 1.0 |
| meta | `insufficient_context` | 1.0 | 0.1 | 1.0 |

Irreversible-or-exfiltration dimensions get the steepest false-allow penalty and the
steepest false-deny penalty too (an irreversible false deny is also expensive: it
blocks something that later turns out benign and unrecoverable-to-redo); everything
else scales down with severity. These are starting points for a bundle author to
override per tenant risk tolerance, not calibrated to any real organization.

### 2.3 The objective

For a bundle's covered dimensions (every `RiskDimension` any rule's `when` tree
references via a `score` leaf), with probability `p_dim` and cost block `c_dim`:

```
E[ALLOW] = Σ_dim  p_dim       * c_dim.allow_if_risky
E[REVIEW] = Σ_dim  c_dim.review                          # same regardless of p_dim
E[DENY]  = Σ_dim  (1 - p_dim) * c_dim.deny_if_benign
```

The engine picks `argmin(E[ALLOW], E[REVIEW], E[DENY])`. Ties resolve to the more
restrictive decision (`DENY` > `REVIEW` > `ALLOW`). A dimension the classification
abstained on, or never scored, contributes nothing to any of the three sums. A fired
`hard` rule still forces `DENY`, overriding the argmin — `hard` is a safety net for
unambiguous cases, independent of the probabilistic reasoning.

`DeterministicPolicyEngine.evaluate` records a `DecisionTrace` (in
`forecheck.contracts`) on the returned `PolicyDecision` whenever `decision_mode` is
`expected_cost`: the mode, the three expected costs, the pre-hard-override argmin,
and whether a hard override was applied. A `threshold`-mode decision carries no
trace (`matched_rules` already replays it fully).

### 2.4 Worked example

Two covered dimensions, `financial_commitment` (p = 0.3) and `privilege_escalation`
(p = 0.1), both using their severity default (`high` tier: `allow_if_risky=5.0`,
`review=0.3`, `deny_if_benign=1.5`):

```
E[ALLOW]  = 0.3*5.0 + 0.1*5.0 = 1.5 + 0.5 = 2.0
E[REVIEW] = 0.3     + 0.3     = 0.6
E[DENY]   = 0.7*1.5 + 0.9*1.5 = 1.05 + 1.35 = 2.4
```

`argmin` is `REVIEW` (0.6), well below both `ALLOW` (2.0) and `DENY` (2.4): neither
dimension alone crosses a threshold-mode deny bar, but the joint evidence is not
cheap enough to allow outright either, so the engine routes to human review instead
of picking a side blindly. `policies/expected-cost-example.yaml` exercises this
shape directly.

## 3. Versioning

Adding `decision_mode` and `cost` is a schema addition; per ADR 0002 the DSL version
moved from `1.0` to `1.1`. The loader (`policies/loader.py`) only rejects a
major-version mismatch, so bundles still declaring `dsl_version: "1.0"` keep
loading unchanged — this field addition does not require touching them.
