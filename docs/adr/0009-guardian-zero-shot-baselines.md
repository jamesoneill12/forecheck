# ADR 0009 — Zero-shot guardian baselines and an identity-ablation switch

Status: accepted, 2026-09-21

## Context

Every existing backend is either ours (decoder, encoder, both trained on forecheck's
own eleven-dimension label schema) or has zero learned parameters
(`rule_baseline`). There is no answer to "what does an existing, widely-used open
safety model score our synthetic splits at, with no forecheck-specific training at
all?" That answer matters as a floor/ceiling check: if a zero-shot guardian model
already scores well on a dimension, the dimension may be easier than intended; if our
trained arms cannot beat it, that is itself a finding.

A second, related question: how much of any backend's score is actually explained by
authorization context (who is asking, what they are allowed to do, what policy
applies) rather than the shape of the action itself? `strip_identity` answers that for
any backend built on `serialize_context`.

## Decision

Add `forecheck.inference.guardian.GuardianBackend`, a third-party adapter over three
open safety models, each scored one `RiskDimension` at a time against a
model-specific natural-language risk/category definition (`dimension_definitions`,
defaulting to text derived from each dimension's docstring in `contracts.enums`):

- `ibm-granite/granite-guardian-3.3-8b` (`granite_guardian`): `apply_chat_template`
  with `guardian_config={"custom_risk_definition": ...}`, assistant turn is the
  proposed action as a tool call; probability read off the `Yes`/`No` first-token
  logits, same candidate-logit approach as ADR 0004.
- `meta-llama/Llama-Guard-4-12B` (`llama_guard`): `apply_chat_template` with a single
  custom category whose description is the dimension definition; probability off
  `unsafe`/`safe`.
- `openai/gpt-oss-safeguard-20b` (`gpt_oss_safeguard`): system prompt carries the
  dimension definition plus the example's policy text; scored by greedy generation
  (`max_new_tokens≈256`) and a verdict parse, at raw score `1.0`/`0.0` rather than a
  real probability -- documented limitation, since gpt-oss-safeguard's public chat
  template has no fixed single-token verdict slot to read logits from.

All three reuse `serialize_context` for the rendered context, so the identity ablation
and truncation behaviour are shared with every other backend.

`strip_identity: bool` is added to `serialize_context` (and threaded through
`GuardianBackend`, `HFBackend`, `EncoderBackend`, and `forecheck evaluate
--strip-identity`): it omits the principal's entitlements, the agent's delegated
scopes, the delegation chain (`on_behalf_of`), and each policy statement's free text,
leaving section structure, other fields, and the non-identity dimensions' inputs
unchanged. A calibration bundle is always fitted on full context, so `evaluate` skips
loading one whenever `--strip-identity` is set, and the report records
`identity_stripped` in its metadata and markdown header.

## Licence notes

- Granite Guardian 3.3: Apache-2.0.
- gpt-oss-safeguard-20b: Apache-2.0.
- Llama Guard 4: gated repository, so the EKS recipe skips it until an `HF_TOKEN` with access is available on the pod; Llama 4 Community License, not Apache/MIT -- usable for evaluation
  and as a baseline, but excluded from anything we would ship or fine-tune under our
  own licence terms. Kept as a baseline-only comparison point given its wide adoption.

## Rejected

- **ShieldGemma**: Gemma's custom licence carries redistribution and use restrictions
  beyond Llama 4's, without a clearer capability edge over the three selected models;
  not worth a second non-permissive licence in the same baseline set.
- **Nvidia Aegis**: weights are not broadly redistributable outside NVIDIA's own
  guardrail stack at the time of writing, and it targets a different (non-agentic,
  content-moderation) label taxonomy than forecheck's action-risk dimensions.

## Consequences

- `resolve_backend("guardian", run, config=<path>)` requires `--backend-config PATH`;
  `run` is created if missing when `--backend guardian`, since a guardian baseline
  carries no forecheck-trained weights or `config.resolved.yaml`.
- `GuardianBackend.capabilities.deterministic` is `False` for `gpt_oss_safeguard`
  only, mirroring `LLMJudgeBackend`'s honesty about its own non-determinism.
- The exact `apply_chat_template` keyword arguments (`guardian_config`, `categories`,
  the tool-call message shape) are unverified against the real tokenizers as of
  writing; they are exercised in tests only against fake tokenizers standing in for
  each family's expected interface, not the real Hugging Face checkpoints.
