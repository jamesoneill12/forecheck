# ADR 0001 — The model scores facts; a separate deterministic engine decides

Status: accepted, 2026-09-20

## Context

Every guardrail system surveyed in `docs/research/` that emits a decision does so
from inside the model (a boolean `attackDetected`, a `malicious`/`benign` label, an
L1–L5 level) or from inside a rules engine with no learned component. None separates
"what is true about this action" from "what our organization permits".

## Decision

forecheck's learned model emits calibrated probabilities over eleven *descriptive*
dimensions and has no `decision` output. A separate policy engine — pure, total,
declarative, hashed — maps scores plus typed context facts to `ALLOW`/`REVIEW`/`DENY`.
The `ClassifyResponse` type has no decision field; the `PolicyDecision` type has no
model access. The separation is enforced by the type system, not by convention.

## Consequences

- Changing a business threshold is a policy commit, not a retraining run.
- Every decision is replayable from the matched rules and auditable against a bundle hash.
- The model must never be trained on normative labels ("allowed"/"denied"); the data
  pipeline derives only descriptive labels from latent facts.
- Callers who want a single "is it safe" number will not get one. That is deliberate.
