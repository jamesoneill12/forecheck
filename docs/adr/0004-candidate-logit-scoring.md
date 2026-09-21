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

The selected base models (see `configs/training/README.md`) are post-trained
instruction models expecting their own chat template. Scoring or training one with the
raw prompt-contract text (as if it were a base model) reads logits at a position the
model was never post-trained to answer at, so `prompt.use_chat_template` (default
`true` for the HF backend and training) now renders `[{"role": "system",
SYSTEM_PREAMBLE}, {"role": "user", context + "\n\n" + question}]` through
`tokenizer.apply_chat_template(..., add_generation_prompt=True, **thinking_kwargs)` and
scores the first assistant token, via one helper (`forecheck.inference.chat_template`)
imported by both `forecheck.inference.hf` and `forecheck.training.dataset` so the two
paths cannot drift apart. `thinking_kwargs` is derived per tokenizer from its chat
template text, since the four selected bases disagree on whether a thinking toggle
exists and, when it does, what keyword selects it (see the chat_template module
docstring).

Shared-prefill KV-cache reuse still applies: the prefix ends where the rendered
context does, located by rendering the template with a sentinel in place of the
question and verified per question by checking that separately tokenizing the prefix
and the (question + template tail) suffix reproduces the full rendered text's token
ids exactly. When that check fails for a given question, scoring falls back to a
single non-shared forward pass for it rather than trusting an unverified split.
`PROMPT_CONTRACT_VERSION` is bumped to `1.1.0` and `use_chat_template`'s default now
participates in `PROMPT_CONTRACT_HASH`, since it changes the literal text a model
sees for the same context.

## Amendment 2026-09-21: base-model swap and per-tokenizer thinking detection

The base-model selection changed to Granite 3.3 (2B/8B), Granite 4.0 Micro (3B) and
OLMo 3 7B (see `configs/training/README.md`); `forecheck.inference.chat_template` now
exposes `thinking_kwargs(tokenizer)`, which inspects the tokenizer's chat template text
for the `enable_thinking` or `thinking` variable name and passes the matching kwarg
(or none) instead of the previous three-way trial-and-error. For a given tokenizer this
changes the literal rendered text versus the old direct-kwarg-only attempt whenever
that tokenizer's template uses the `thinking` convention (Granite 3.3) rather than
`enable_thinking`, so `PROMPT_CONTRACT_VERSION` is bumped to `1.2.0`.

## Amendment 2026-09-21 (b): four-message layout for a stable prefill split

A real training run hit `DataDisciplineError` on every `ibm-granite/granite-3.3-2b-instruct`
example for `QUESTIONS[RiskDimension.PROMPT_INJECTION_INFLUENCE]` ("Is the proposed
action..."). `build_chat_messages` packed context and question into one user message
(`f"{context_text}\n\n{question}"`); Granite's tokenizer BPE-merges across the `\n\n` +
`Is` boundary, so `plan_chat_prefill`'s prefix/suffix retokenization no longer
reproduced the full tokenization, and `_encode_shared_chat` raised rather than
building a shared-prefill sequence.

`build_chat_messages` now renders four messages: `[system: SYSTEM_PREAMBLE] [user:
context_text] [assistant: CONTEXT_ACK] [user: question]`, where `CONTEXT_ACK` is a
fixed short string ("Understood. Ask your question about this action.") defined next
to `SYSTEM_PREAMBLE` in `forecheck.inference.prompt` and folded into
`PROMPT_CONTRACT_HASH`. The prefix/suffix split now falls on the second user turn's
role-header special token rather than on plain rendered text, so a BPE merge cannot
cross it on any tokenizer with special role tokens. `plan_chat_prefill` keeps its
sentinel-render-and-retokenize verification and its `None` fallback to a non-shared
forward pass unchanged, as the safety net for tokenizers where this still fails.
`PROMPT_CONTRACT_VERSION` is bumped to `1.3.0`.
