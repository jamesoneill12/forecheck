# Architecture

## 1. The shape of the system

```
                       ┌──────────────────────────────────────────────────────────┐
                       │  forecheck.contracts   (the only place wire types live)  │
                       └──────────────────────────────────────────────────────────┘
                                 ▲                 ▲                  ▲
          ┌──────────────────────┴───┐   ┌─────────┴─────────┐   ┌────┴──────────────────┐
          │  DATA                    │   │  MODEL            │   │  DECISION             │
          │  generation/ → data/     │   │  inference/       │   │  policies/            │
          │  validation/             │   │  calibration/     │   │                       │
          │  latent ─▶ labels        │   │  training/        │   │  scores + facts ─▶    │
          │  latent ─▶ ActionContext │   │  context ─▶ raw   │   │  ALLOW/REVIEW/DENY    │
          │                          │   │  raw ─▶ probability│  │                       │
          └──────────────┬───────────┘   └─────────┬─────────┘   └────────────┬──────────┘
                         │                         │                          │
                         ▼                         ▼                          ▼
                 ┌────────────────────────────────────────────────────────────────────┐
                 │  evaluation/   metrics · CIs · slices · consistency · decisions     │
                 └────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
                 ┌────────────────────────────────────────────────────────────────────┐
                 │  api/  FastAPI · auth hooks · audit/redaction · metrics · OTel      │
                 │  integrations/  SDK · tool-dispatch middleware · MCP interceptor    │
                 └────────────────────────────────────────────────────────────────────┘
```

Three vertical slices — data, model, decision — meet only through `forecheck.contracts`
and are exercised together only by `evaluation/` and `api/`. Each slice can be replaced
wholesale: a different generator, a different backend, a different policy engine.

## 2. Request path

```
ClassifyRequest
   │  validate (Pydantic, contracts/limits)               ← hard limits, typed errors
   ▼
ActionContext
   │  serialization.render_context()                      ← canonical, fenced, trust-labelled
   ▼                                                        text; escapes delimiters in
prompt text (+ TruncationInfo)                              untrusted content; truncates in
   │  backend.score()                                       documented priority order
   ▼
RawScores  {dimension: log-odds}                          ← mock | hf (candidate-logit,
   │  Classifier.apply_calibration()                        shared prefill) | rule_baseline
   ▼
ClassifyResponse  {dimension: probability | abstained}    ← probability ONLY if a
   │                                                        CalibratorBundle whose
   │  (optional) PolicyEngine.evaluate(response, context)   prompt_contract_hash and
   ▼                                                        label_schema_version match
PolicyDecision  {ALLOW|REVIEW|DENY, matched_rules, bundle_hash}
```

The model is invoked exactly once per request regardless of how many dimensions are
requested: the context is prefilled once and each dimension costs one short question and
a two-token logit read (ADR 0004).

## 3. Data path

```
generation/scenarios      LatentScenario samplers, one per tool family, seeded
        │
        ▼
data/contrastive          flip exactly one latent field → paired LatentScenario
        │
        ├──────────────▶  data/labeling.derive_labels()      → LabelSet   (pure code)
        │
        └──────────────▶  generation/renderers                → ActionContext
                              OfflineTemplateRenderer (no network)
                              LLMRenderer (surface text only; keys from env)
                                    │
                                    ▼
                          validation/validators               rendering preserved the
                                    │                          latent facts? else discard
                                    ▼
                          Example {latent, context, labels, provenance, transformation}
                                    │
                                    ▼
                          data/splitting                       group by template ancestry;
                                    │                          pairs never straddle;
                                    ▼                          eval_only/canary refused
                          {train, calibration, dev, test,      from train + calibration
                           heldout_family, adversarial}.jsonl
                                    + DatasetManifest (sha256, positive rates, family digest)
```

Labels flow *from* the latent scenario; text flows *from* the latent scenario. Nothing
flows from text to labels (ADR 0003).

## 4. Module responsibilities

| Package | Owns | Must not |
|---|---|---|
| `contracts/` | Every wire type, enum, limit, the latent schema, the record schema | Import anything else in forecheck |
| `data/` | Tool catalogue, label derivation, offline rendering, contrastive pairs, splitting, JSONL I/O, manifests | Call a network or a model |
| `generation/` | Scenario samplers, renderer protocol + implementations, the pipeline (seeds, cache, retries, cost, rate limit, resume) | Assign labels |
| `validation/` | Check a rendered `ActionContext` against its `LatentScenario` | Repair a rendering |
| `inference/` | Prompt contract + hash, serialization + truncation, backends (`mock`, `hf`), the `Classifier` facade | Threshold, decide, or emit a probability without a calibrator |
| `calibration/` | Calibrator methods, fitting on the calibration split, artifact store, calibration metrics | Touch model weights |
| `training/` | Config, dataset → candidate-token targets, LoRA/QLoRA loop, resume, config capture, data hashes, tracking | Read `test` or `calibration` |
| `evaluation/` | Metrics, bootstrap, slices, consistency, selective, decision cost, latency, runner, report, baselines | Produce a report without an evaluation class |
| `policies/` | DSL schema, loader + hash, deterministic engine, fact table, shipped bundles | I/O, model access, randomness |
| `api/` | FastAPI app, settings, auth hooks, audit logging + redaction, Prometheus, OTel, warm-up, shutdown | Store request bodies by default |
| `integrations/` | Python SDK, tool-dispatch middleware, MCP interceptor | Bypass the contract |

## 5. Backends

`inference/base.py` defines `ClassifierBackend`. Implementations:

| Backend | Purpose | Deterministic | Needs |
|---|---|---|---|
| `MockBackend` | Exercise the full API + policy path with no model; transparent heuristics + seeded jitter. **Not a model; not for production.** | yes | nothing |
| `RuleBaselineBackend` | Evaluation floor: what typed facts alone achieve | yes | nothing |
| `HFBackend` | Real scoring: HF decoder + optional LoRA, candidate-logit, shared prefill with verified fallback; CUDA → MPS → CPU | yes (greedy logits) | `forecheck[torch]` |
| `LLMJudgeBackend` | Baseline: generative judge per dimension; uncalibrated by construction | no | an API key (optional) |

All backends return log-odds-like raw scores; the mock returns [0,1] and says so in
`model_info`. Only `calibration/` interprets them.

## 6. Calibration artifacts

```
runs/<run>/
  adapter/                 LoRA weights (safetensors)
  config.resolved.yaml     every hyperparameter, resolved
  data_hashes.json         sha256 of every split consumed
  prompt_contract.json     template, questions, field order, hash
  calibration/
    bundle.json            CalibratorBundle: per-dimension params + provenance + ECE
    bundle.json.sha256
  reports/
    test.synthetic_in_distribution.{json,md}
    heldout_family.synthetic_heldout_adversarial.{json,md}
```

Calibration is a separate artifact so it can be refit on a deployment's traffic without
touching weights (ADR 0005). The `Classifier` refuses a bundle whose
`prompt_contract_hash` or `label_schema_version` does not match the running code.

## 7. Policy engine

```
ClassifyResponse ──┐
                   ├──▶  facts = derive_facts(context)        typed, documented table
ActionContext  ────┘             │
                                 ▼
                    for rule in bundle.rules:
                        cond = eval(rule.when, scores, facts)   three-valued: T / F / UNKNOWN
                        UNKNOWN → bundle.unknown_as             (worst_case default)
                        if T: matched.append(rule)
                    decision = most_restrictive(matched) or bundle.default_decision
                    if not response.calibration.is_calibrated and not bundle.allow_uncalibrated:
                        decision = bundle.uncalibrated_decision
```

Pure function. Hash of the canonical bundle in every decision. Unknown dimension or fact
names are load-time errors (ADR 0007).

## 8. Serving

FastAPI, async request handling with the model call offloaded to a bounded thread pool
(or an async batcher for the HF backend, where batching is safe because scoring is
stateless). `/health/ready` is false until warm-up has run one synthetic request through
the backend. Graceful shutdown drains in-flight requests. Every response carries
`model.prompt_contract_hash`, `calibration.method` and — on the policy route —
`policy_bundle_hash`, so an audit line is sufficient to reproduce a decision.

Audit logging emits structured events containing request id, tenant id, principal id,
agent id, tool name, argument digest, per-dimension probabilities, decision, matched rule
ids and bundle hash. Argument *values*, observation content and objective text are never
logged. Request bodies are not stored unless `FORECHECK_STORE_REQUEST_BODIES=true`.

Tenant isolation is a boundary, not a feature: `principal.tenant_id` is carried into
every audit record and metric label; policy bundles may be selected per tenant; no
request state is shared across requests.

## 9. Training

`training/` consumes `train` only, uses `dev` for model selection, and never opens
`calibration` or `test`. Targets are the candidate-token ids for "yes"/"no" per
dimension; the loss is cross-entropy over that two-way set at the answer position for
each of the eleven questions, with the shared prefill computed once per example.
Configs for ~1B, ~4B and ~8–9B live in `configs/training/`; a `smoke` config trains a
tiny model for a few steps on the fixtures and runs in CI on CPU. Every run records the
resolved config, the git SHA, the data hashes and the prompt contract beside the
adapter.

## 10. What is deliberately absent

- No Kubernetes manifests or cloud-specific infrastructure in the core repo. The
  `configs/eks/` recipe is a submission template for one specific team pool and is
  documented as such.
- No caching of classifications. Two identical requests are two model calls; the
  time-of-check/time-of-use analysis (threat model TM-12) depends on it.
- No "safe" boolean anywhere.
