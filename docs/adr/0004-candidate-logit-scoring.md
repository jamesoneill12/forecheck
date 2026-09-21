# ADR 0004 — Score by reading candidate-token logits, not by generating

Status: accepted, 2026-09-20

## Context

Generative judges pay full decode latency, can be steered into emitting anything, and
give a text label that must then be parsed. Bespoke Nimble (see `docs/research/01`)
demonstrates that a small LoRA-tuned decoder scoring constrained candidate tokens over a
shared prefill is fast and trainable with plain cross-entropy over the candidate set.

## Decision

The Hugging Face backend encodes the serialized context once (`use_cache=True`), then
for each of the eleven dimensions appends a short fixed question and reads the logits
at the final position restricted to the "yes"/"no" candidate token sets. The raw score
is the log-odds over that renormalized two-way set. Training minimizes cross-entropy
over the same candidate set. There is no free-form generation path.

A correct fallback concatenates full sequences per question when KV reuse is not
supported by the model or cache implementation; support is detected, not assumed.

## Consequences

- Eleven questions cost one prefill plus eleven short decodes.
- There is no generation channel for an injected observation to hijack; the worst an
  attacker can do is move a number, and the adversarial evaluation slice measures that.
- The raw log-odds is not a probability. ADR 0005 governs what is.

## Amendment 2026-09-20: chat-template scoring

The selected base family, Qwen3.5 (see `configs/training/README.md`), is post-trained
to expect its own chat template and defaults to thinking mode. Scoring or training it
with the raw prompt-contract text (as if it were a base model) reads logits at a
position the model was never post-trained to answer at, so `prompt.use_chat_template`
(default `true` for the HF backend and training) now renders `[{"role": "system",
SYSTEM_PREAMBLE}, {"role": "user", context + "\n\n" + question}]` through
`tokenizer.apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)`
and scores the first assistant token, via one helper
(`forecheck.inference.chat_template`) imported by both `forecheck.inference.hf` and
`forecheck.training.dataset` so the two paths cannot drift apart.

Shared-prefill KV-cache reuse still applies: the prefix ends where the rendered
context does, located by rendering the template with a sentinel in place of the
question and verified per question by checking that separately tokenizing the prefix
and the (question + template tail) suffix reproduces the full rendered text's token
ids exactly. When that check fails for a given question, scoring falls back to a
single non-shared forward pass for it rather than trusting an unverified split.
`PROMPT_CONTRACT_VERSION` is bumped to `1.1.0` and `use_chat_template`'s default now
participates in `PROMPT_CONTRACT_HASH`, since it changes the literal text a model
sees for the same context.
