# ADR 0003 — Labels are derived from latent facts by code, never assigned by a model

Status: accepted, 2026-09-20

## Context

Teacher-model labelling of agent-action safety data inherits the teacher's biases and,
worse, its conflation of "risky" with "disallowed". It also makes minimal contrastive
pairs approximate: the teacher may or may not flip when the one relevant fact flips.

## Decision

The pipeline is `LatentScenario → LabelSet` via `forecheck.data.labeling.derive_labels`
(pure, unit-tested per rule) and `LatentScenario → ActionContext` via a renderer. An LLM
may only render surface text. A validator checks the rendering preserved the latent
facts; a rendering that does not is discarded, never relabelled.

Contrastive pairs are constructed by flipping exactly one latent field, so the label
delta is provably attributable to that field. `SURFACE_PARAPHRASE` pairs must produce
byte-identical label sets and are used to measure invariance.

## Consequences

- A labelling bug is a code bug with a failing test, not a dataset artefact to be
  discovered by inspection.
- `LabelValue.NOT_APPLICABLE` is representable and is excluded from metrics rather
  than counted as a negative.
- The label rules are exported as `LABEL_DERIVATION_RULES` and the data card is
  generated from them, so documentation cannot drift from behaviour.
- Coverage is bounded by what the latent schema can express. New threat shapes require
  a schema extension, which is the right place for that decision to be visible.
