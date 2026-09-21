# Built-in policy bundles

Three shipped bundles, loaded via `forecheck.policies.builtin.load_builtin_engine(name)`
or directly via `forecheck.policies.loader.load_bundle_file(path)`. Each is real,
defensible policy for a specific operating posture, not a placeholder.

| Bundle | `default_decision` | `unknown_as` | When to use |
| --- | --- | --- | --- |
| `conservative` | `review` | `worst_case` | New deployments, tenants without established calibration confidence, or any environment where an unreviewed false ALLOW is worse than an unnecessary REVIEW. Every dimension has a low deny/review threshold; only a single narrow, audited `allow_override` rule can reach ALLOW without a human having looked at the classification first in spirit (the override itself still requires explicit authorization facts to be true). |
| `balanced` | `allow` | `worst_case` | The default operating posture once a tenant's calibration has been validated (`CalibrationInfo.method is not NONE` and ECE is acceptable). Same eight deny categories as `conservative`, at meaningfully higher thresholds, with more REVIEW outcomes in the middle band. Reversible, non-mutating, untrusted-content-free development-stage actions ALLOW freely via an `allow_override` rule. |
| `permissive` | `allow` | `worst_case` | **Development environments only.** Denies only four genuinely unambiguous cases: injection driving an irreversible action, injection driving a financial commitment, exfiltration of SECRET-classified data, and unambiguous privilege escalation. Everything else in development ALLOWs via an `allow_override` rule that explicitly cannot beat those four `hard` denies. **Do not point this bundle at a staging or production tenant.** It is intentionally under-restrictive so that agent development is not blocked by REVIEW/DENY on ordinary, low-stakes dev-loop actions. |

## Shared design points across all three

- **Fail closed on uncertainty.** All three bundles set `unknown_as: worst_case`: an
  abstained `RiskDimension` or a context fact that could not be derived is never
  silently treated as "no risk". See `forecheck.policies.engine` for the exact
  resolution rule (a restrictive rule's condition resolves an unknown as matching; an
  `allow`-decision rule's condition resolves it as not matching).
- **Fail closed on uncalibrated scores.** All three bundles set
  `allow_uncalibrated: false`. If `CalibrationInfo.method is NONE`, evaluation returns
  `uncalibrated_decision` (`review` in all three) without evaluating any rule against
  raw scores. A tenant that wants to thread raw, uncalibrated scores through its rules
  anyway must opt in explicitly by forking a bundle with `allow_uncalibrated: true`,
  at which point every decision carries a `log_to_audit_sink` warning obligation.
- **No tool is ever denied by name alone.** Authorization depends on identity, intent,
  context, sequence, destination and tenant policy, not on which tool was called.
  Every condition branches on a typed context fact or a model score; none of the three
  bundles contains a bare `fact: tool_name` rule.
- **`hard: true` denies cannot be overridden.** Each bundle's unambiguous-deny rules are
  flagged `hard`, so no `allow_override` rule in that bundle -- however broad -- can
  turn one of those specific fired denies into an ALLOW.

## Expected-cost decision mode

All three bundles above use `decision_mode: threshold` (the default): most-restrictive
rule wins. `expected-cost-example.yaml` demonstrates the alternative,
`decision_mode: expected_cost`, which picks whichever of ALLOW/REVIEW/DENY minimises
expected cost over the bundle's covered dimensions' probabilities jointly, rather than
each rule checking only its own threshold. See `docs/policy-dsl.md` for the DSL
fields, the severity-derived default cost table, and a worked example.

## Choosing a bundle at runtime

`policy_bundle_id` on a `PolicyEvaluateRequest` selects one of these by name (or a
tenant-custom bundle, once that lookup path exists outside this package). There is no
bundle that is safe to use for both development and production traffic: use
`conservative` or `balanced` in production, `permissive` only in development.
