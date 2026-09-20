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
