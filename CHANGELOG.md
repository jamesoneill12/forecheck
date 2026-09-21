# Changelog

All notable changes to forecheck. Format follows Keep a Changelog; versions follow
SemVer. The wire contract, label schema, prompt contract and policy DSL are versioned
separately — see ADR 0002.

## [Unreleased]

### Added
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

### Not yet
- Published trained weights.
- Any human-labelled gold set or external-benchmark result.
