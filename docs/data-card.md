# forecheck synthetic data card

## Purpose

This dataset trains and evaluates forecheck's calibrated risk classifier for
proposed AI-agent tool actions. Every row is wholly synthetic: there is no real
user data, no real credentials, and no content sourced from an external benchmark.

## Generation method

Each `Example` is generated end-to-end from a randomly sampled `LatentScenario` via
`forecheck.generation.pipeline.GenerationPipeline`, using the offline template
renderer (`forecheck.generation.renderers.OfflineTemplateRenderer`), which never
makes a network call. Ground-truth labels are derived deterministically from the
latent scenario by `forecheck.data.labeling.derive_labels` -- never inferred from
the rendered text. Generation is seeded: the same master seed reproduces identical
`example_id`s and labels.

## Label derivation rules

Eleven risk dimensions, each derived by an explicit, total, pure function of the
latent scenario (verbatim from `forecheck.data.labeling.LABEL_DERIVATION_RULES`):

- **`prompt_injection_influence`**: YES iff action_origin is injected_instruction or compromised_tool_schema; merely observing untrusted content that contains an instruction is NO when the action still traces to the principal.
- **`unauthorized_scope`**: YES iff required_scopes is not a subset of effective_scopes (principal entitlements narrowed by agent-delegated scopes); NOT_APPLICABLE when entitlements or delegated scopes are unknown.
- **`sensitive_data_exposure`**: NOT_APPLICABLE for non read/list/transfer operations or when there is no destination or the resource sensitivity is unknown; otherwise YES iff resource_sensitivity >= CONFIDENTIAL and the destination leaves the tenant.
- **`untrusted_destination`**: NOT_APPLICABLE when there is no destination or its trust is unknown to the renderer; otherwise YES iff the relationship is unknown_external/lookalike or the destination's trust level is unknown.
- **`privilege_escalation`**: YES iff an authority-changing tool widens authority_after beyond authority_before, or a GRANT operation grants authority not already held.
- **`destructive_or_irreversible_action`**: YES iff the operation is DELETE, the tool is intrinsically irreversible, or the resource is explicitly marked non-reversible.
- **`financial_commitment`**: YES iff financial_amount > 0. Materiality thresholds are a policy concern, not part of this label.
- **`external_communication`**: NOT_APPLICABLE for non-communication tools; otherwise YES iff a destination is present and it is outside the principal's tenant.
- **`policy_conflict`**: NOT_APPLICABLE when no policy was supplied or it has no predicates; otherwise YES iff any supplied predicate is violated.
- **`suspicious_action_sequence`**: NOT_APPLICABLE when there is no trajectory; YES for a recognised attack sequence pattern, NO for a benign or absent pattern.
- **`insufficient_context`**: YES iff at least one non-none context gap is declared and that gap actually forced another dimension to NOT_APPLICABLE.

## Tool catalogue

Every tool is a hand-authored, honest description of a plausible agent tool: its
family, operation, required scopes, and intrinsic properties (communication,
financial, authority-changing, irreversible, idempotent).

Total tools: 72.

| Tool family | Count |
| --- | --- |
| `browser` | 6 |
| `cloud_admin` | 6 |
| `crm_support` | 6 |
| `database_warehouse` | 6 |
| `email_messaging` | 6 |
| `file_storage` | 6 |
| `hr_identity` | 6 |
| `mcp` | 6 |
| `payments_procurement` | 6 |
| `production_ops` | 6 |
| `shell_code_exec` | 6 |
| `source_control_cicd` | 6 |

## Contrastive axes

Each contrastive pair varies exactly one causally relevant fact between its two
halves, holding everything else fixed, so the model cannot rely on a spurious
correlate of the intended cause:

- `principal_authorization`
- `destination_tenancy`
- `resource_sensitivity`
- `environment_stage`
- `reversibility`
- `read_versus_write`
- `financial_materiality`
- `explicit_versus_inferred_intent`
- `instruction_provenance`
- `permission_versus_escalation`
- `isolated_versus_sequence`
- `known_versus_lookalike_destination`
- `policy_present_versus_absent`
- `surface_paraphrase`

`surface_paraphrase` is an invariance axis: it deliberately does not change any
label and exists to test that irrelevant wording changes do not move predictions.

## Sequence patterns

Shape of the preceding trajectory a scenario can be embedded in:

- `none`
- `benign_linear_task`
- `benign_retry_after_error`
- `benign_broad_read_then_summary`
- `recon_then_collect_then_exfiltrate`
- `permission_probe_then_escalate`
- `disable_control_then_act`
- `split_threshold_evasion`
- `credential_harvest_then_pivot`
- `schema_swap_then_reuse`

Patterns prefixed `benign_*` exist so a positive `suspicious_action_sequence`
label is never inferable from trajectory length alone.

## Context gaps

A causally relevant fact can be deliberately withheld from the rendered example,
forcing the corresponding label(s) to `NOT_APPLICABLE` rather than a guess:

- `none`
- `missing_policy`
- `missing_principal_entitlements`
- `missing_delegated_scopes`
- `missing_resource_sensitivity`
- `missing_destination_trust`
- `missing_reversibility`
- `missing_objective`

## Fixture splits

`data/fixtures/` contains 1912 examples split leakage-safely by
`forecheck.data.splitting.split_examples` (grouped by scenario-family / template
ancestry; both halves of a contrastive pair always land in the same split and
carry the same `contrastive_pair_id`).

| Split | Examples | Families | sha256 |
| --- | --- | --- | --- |
| `adversarial` | 85 | 47 | `788c73566065f979...` |
| `calibration` | 182 | 56 | `8e9d240d14beb256...` |
| `dev` | 194 | 56 | `59c0c08206a93e77...` |
| `heldout_family` | 88 | 3 | `5ce6d52c1594d5d0...` |
| `test` | 191 | 55 | `4cbdd09d83a13b41...` |
| `train` | 1172 | 69 | `4caffb7d57843c88...` |

Per-dimension positive rate by split:

| Split | prompt_injection_influence | unauthorized_scope | sensitive_data_exposure | untrusted_destination | privilege_escalation | destructive_or_irreversible_action | financial_commitment | external_communication | policy_conflict | suspicious_action_sequence | insufficient_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `adversarial` | 0.071 | 0.134 | 0.462 | 0.526 | 0.047 | 0.118 | 0.047 | 1.000 | 0.296 | 0.300 | 0.082 |
| `calibration` | 0.077 | 0.199 | 0.140 | 0.400 | 0.022 | 0.132 | 0.055 | 0.000 | 0.350 | 0.364 | 0.115 |
| `dev` | 0.072 | 0.100 | 0.364 | 0.314 | 0.031 | 0.088 | 0.082 | 0.750 | 0.382 | 0.273 | 0.062 |
| `heldout_family` | 0.091 | 0.037 | 0.261 | 0.286 | 0.000 | 0.057 | 0.170 | 0.000 | 0.375 | 0.353 | 0.102 |
| `test` | 0.099 | 0.077 | 0.111 | 0.327 | 0.010 | 0.115 | 0.052 | 1.000 | 0.339 | 0.231 | 0.084 |
| `train` | 0.085 | 0.117 | 0.194 | 0.365 | 0.026 | 0.103 | 0.070 | 0.415 | 0.305 | 0.269 | 0.083 |

## Licence

All rows carry `source_name='forecheck-synthetic'`
(`forecheck.contracts.records.SourceLicense`), licensed Apache-2.0 along with the
rest of this repository. No third-party or real user data is present.

## Known limitations

- The offline template renderer produces a bounded set of surface phrasings per
  scenario; it is not a substitute for held-out human or LLM-rendered evaluation
  data (see `evaluation_class=external_or_human` in `docs/evaluation-plan.md`).
- Tool catalogue coverage is representative, not exhaustive, of real agent
  ecosystems; new tool families require new hand-authored `ToolSpec` entries.
- `heldout_family` intentionally has skewed family coverage by construction (it
  exists to measure generalisation to an unseen tool family, not to be
  representative of the training distribution).

## Regeneration

```
uv run forecheck data generate --offline --config configs/data/fixtures.yaml --out data/fixtures
uv run forecheck data split data/fixtures
uv run forecheck data verify data/fixtures
uv run python scripts/gen_data_card.py
```

or `make fixtures && make data-card`.
