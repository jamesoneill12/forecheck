# ADR 0008 — Add an encoder classifier arm alongside the decoder

Status: accepted, 2026-09-21

## Context

The only trained scoring path today is ADR 0004's decoder candidate-logit backend: a
LoRA-tuned instruction model reading a "yes"/"no" log-odds off appended per-dimension
questions. That path pays for a generative model's full parameter count and
autoregressive machinery to answer eleven binary questions per action -- decode cost
that a much smaller bidirectional encoder with a linear head does not need to pay.
`docs/results/2b-synthetic-v1` also found that base model capacity was never the
binding constraint on the v1 result: the 2B decoder already saturates the synthetic
in-distribution metric, so a cheaper backbone is not obviously giving anything up on
that axis. What is genuinely open is out-of-distribution generalization -- whether a
bidirectional encoder trained on a dense pooled representation of the whole context
generalizes differently than a decoder reading local per-question logits, particularly
under `synthetic_heldout_adversarial`. Running both arms side by side, sharing every
downstream layer (calibration, policy, evaluation, serving), makes that a controlled
comparison rather than a rewrite.

## Decision

Add `forecheck.inference.encoder.EncoderBackend`, a second implementation of the same
`ClassifierBackend` protocol the decoder backend satisfies. It serializes an
`ActionContext` with the same `serialize_context` the decoder uses (no chat template,
no per-dimension question -- the encoder never sees either), pools an encoder
backbone's final hidden states (`mean` or `cls`, backbone-dependent), and reads all
eleven per-dimension logits off one linear head. Because a question never gets
appended, the encoder's raw score does not depend on `PROMPT_CONTRACT_HASH`'s question
set or chat-template default; it depends only on the section order and preamble text
`serialize_context` actually renders, so `ModelInfo.prompt_contract_hash` for this
backend is a new, narrower `serialization_contract_hash()` rather than the decoder's
hash.

Training lives in `forecheck.training.encoder_loop`, mirroring
`forecheck.training.loop`'s shape (seeded resumable sampling, `LocalJsonTracker`,
run-dir capture, dev macro-AUPRC early stopping) but minimizing masked
BCE-with-logits over the eleven dimensions instead of candidate-token cross-entropy;
`NOT_APPLICABLE`/`UNDETERMINED` cells are excluded from the loss the same way the
decoder excludes them. Two bases are configured, both Apache-2.0: `answerdotai/
ModernBERT-large` (mean pooling) and `ibm-granite/granite-embedding-english-r2` (CLS
pooling, per its model card).

Snowflake's `arctic-embed` family was considered and rejected: it is initialized from
BAAI's `bge-m3`, a Chinese-origin model, which the org's restricted-AI-models policy
bars from training infrastructure regardless of retrieval benchmark quality (the same
policy that moved `forecheck`'s own base-model selection off Qwen; see
`docs/data-card.md` / `restricted-ai-models-policy-no-qwen` memory).

## Consequences

- `calibrate`/`evaluate`/`serve` require no code changes: they consume `RawScores` and
  `ClassifierBackend` through the same protocol, so `--backend encoder` is a
  `resolve_backend` branch, not a new code path through those layers.
- The encoder arm's raw score is a per-dimension logit rather than a two-way
  candidate-token log-odds; both are log-odds scale and both need a fitted calibrator
  before either is a probability, so ADR 0005 is unaffected.
- Comparing the two arms' `synthetic_heldout_adversarial` numbers is now possible
  without conflating backbone family with prompting strategy, since both share the
  serialized-context input and the labelled dataset.
- A calibration bundle fitted on one arm never silently applies to the other:
  `evaluate`'s existing `backend_model_id` match check (ADR 0004) already refuses a
  mismatched bundle, and the encoder's `model_info.model_id` is its own base model id.

## Rejected: Arctic-Embed as a third base

Would have added stronger retrieval-benchmark numbers, but its BAAI `bge-m3`
initialization is Chinese-origin lineage that org policy prohibits on training infra;
not evaluated further.
