# Changelog

All notable changes to forecheck. Format follows Keep a Changelog; versions follow
SemVer. The wire contract, label schema, prompt contract and policy DSL are versioned
separately — see ADR 0002.

## [Unreleased]

### Added
- Expected-cost decision mode for the policy engine (`policy DSL` 1.0 -> 1.1, additive,
  ADR 0002): `PolicyBundle.decision_mode: threshold | expected_cost` and an optional
  per-rule `cost: {allow_if_risky, review, deny_if_benign}` block, with a
  severity-derived default cost table (`default_cost_for_dimension` in
  `policies/dsl.py`). Under `expected_cost`, `DeterministicPolicyEngine` picks the
  ALLOW/REVIEW/DENY that minimises expected cost over the bundle's covered
  dimensions' probabilities jointly (`policies/engine.py::expected_costs`), ties break
  to the more restrictive decision, and a fired `hard` rule still forces DENY. Records
  a `DecisionTrace` (mode + the three expected costs + pre-override argmin) on
  `PolicyDecision` when this mode is used. New `expected_cost_joint` strategy in
  `evaluation/stacking.py` and a property test
  (`test_expected_cost_joint_fpr_bounded_while_independent_fpr_grows_with_k`) showing
  its false-positive rate stays bounded as k grows where `independent`'s does not.
  New example bundle `policies/expected-cost-example.yaml`. Documented in
  `docs/policy-dsl.md` and `docs/evaluation/multi-policy-stacking.md`. The loader now
  only rejects a major `dsl_version` mismatch, so existing `1.0` bundles are unaffected.
- Feedback contract and flywheel: `FeedbackRecord`/`FeedbackAck` in `contracts/io.py`,
  a new `FeedbackOutcome` enum (`approved`/`rejected`/`modified`/`escalated`/`expired`),
  a `POST /v1/feedback` route backed by a pluggable `FeedbackSink` (default: an
  append-only JSONL file under `FORECHECK_FEEDBACK_SINK_PATH`), `client.feedback(...)`
  on both the sync and async SDK clients, an offline `examples/feedback_roundtrip.py`
  showing a `REVIEW` -> human decision -> feedback round trip, and a
  `forecheck feedback export --sink-dir --since --format jsonl` CLI command.
  `schema_version` is unchanged (new models, no fields added to existing ones).
- `docs/evaluation/approval-elimination.md`: precise definitions of approvals
  eliminated and incident rate, the mapping onto `evaluation/selective.py`'s
  risk-coverage machinery and `evaluation/decisions.py`'s `HIGH_SEVERITY_DIMENSIONS`,
  and the exact report shape a future `forecheck evaluate --approval-curve` would
  print. Not implemented — `cli_cmds/evaluate.py` is under separate concurrent work.
- `docs/product-spec.md` reframed around four product pillars (approval elimination,
  delegated-authority conformance, the label flywheel, multi-policy composition) ahead
  of the dimension/wire-contract mechanics, plus an explicit "what we are not" section
  naming Prompt Guard 2, Llama Guard 4, Granite Guardian and ShieldGemma as the
  content-safety tooling forecheck is not competing with.
- Versioned request/response contract (`schema_version` 1.0) with eleven descriptive
  risk dimensions, calibration metadata, abstention, truncation reporting and a stable
  error envelope.
- Latent-scenario data model; deterministic label derivation; offline template
  renderer; contrastive-pair construction across fourteen axes; family-level
  leakage-safe splitting with checksummed manifests.
- Mock backend (heuristic, not a model) and Hugging Face candidate-logit backend with
  shared-prefill scoring and a verified fallback; `ChatPrefillPlanner` caches the
  per-context prefix and the per-question suffix/verdict so scoring renders the chat
  template once per row instead of twice per question.
- Post-hoc calibration (temperature, vector, isotonic, beta) fitted on a dedicated
  split and persisted separately from weights.
- Evaluation suite: per-dimension and calibration metrics with bootstrap CIs, slices,
  contrastive consistency, invariance, selective risk, decision-cost, latency harness;
  every report states its evaluation class.
- Declarative YAML policy DSL, deterministic engine and three shipped bundles.
- FastAPI service, Python SDK, middleware and MCP interceptor examples.
- Research landscape, threat model, product spec, architecture, evaluation plan, data
  card, model card template, seven ADRs.
- Base-model selection: Granite 3.3 (2B/8B), Granite 4.0 Micro (3B), OLMo 3 7B — all
  Apache-2.0.
- Encoder classifier arm (ADR 0008): `EncoderBackend` pools an encoder backbone
  (ModernBERT-large or granite-embedding-english-r2, both Apache-2.0) and reads all
  eleven dimensions off one linear head; `forecheck train-encoder` trains it with
  masked BCE-with-logits; plugs into `calibrate`/`evaluate` via the existing
  `resolve_backend` protocol with no changes to either.
- Zero-shot guardian baselines (ADR 0009): `GuardianBackend` scores Granite Guardian
  3.3 8B, Llama Guard 4 12B and gpt-oss-safeguard-20b against our eleven dimensions
  with no forecheck-specific training, via `forecheck evaluate --backend guardian
  --backend-config <yaml>`. `strip_identity` identity-ablation switch added to
  `serialize_context` and threaded through `GuardianBackend`/`HFBackend`/
  `EncoderBackend` and `forecheck evaluate --strip-identity`; calibration is skipped
  when stripping identity and `identity_stripped` is recorded on every report.
- Policy-generalisation testing (ADR 0010): seven new `PolicyPredicateKind` members
  (`forbid_bulk_above_n`, `require_ticket_reference`, `forbid_outside_business_hours`,
  `forbid_recipient_domain`, `require_dry_run_first`, `data_residency_region`,
  `forbid_pii_field_export`), each evaluable from the latent scenario alone and
  rendered into the existing `ActionContext` fields with no prompt-contract change;
  four clause paraphrases per policy kind (old and new), keyed by a new
  `PolicyPredicate.paraphrase_index`. Two new eval splits, `heldout_policy_kind` and
  `heldout_policy_phrasing`, measure generalisation to a policy kind and a policy
  wording never seen in training respectively.
- Multi-policy stacking evaluation (`evaluation/stacking.py`): for k = 1..K policies,
  compares OR-ing k independently-evaluated guards against merging their rules into one
  bundle and evaluating it once with the existing policy engine, reporting
  false-positive/false-negative/review rate and decision cost per (k, strategy).
  `forecheck evaluate --stacking-bundles <names/paths> --stacking-synthetic` (the latter
  builds 11 single-dimension policies from the threshold-selection split); rendered in
  `report.md` under "Multi-policy stacking". See `docs/evaluation/multi-policy-stacking.md`.

### Not yet
- Published trained weights.
- Any human-labelled gold set or external-benchmark result.
