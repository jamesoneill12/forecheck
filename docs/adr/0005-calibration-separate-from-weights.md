# ADR 0005 — Calibration is a separate, versioned artifact fitted on a dedicated split

Status: accepted, 2026-09-20

## Context

Every surveyed system that outputs a number either does not describe it as calibrated
or (Jev) claims calibration without published methodology. Independent work shows
injection classifiers of this class are actively miscalibrated under attack-distribution
shift. A number a downstream team thresholds on had better mean what it appears to.

## Decision

- The dataset has a `calibration` split used for nothing else — not training, not model
  selection, not threshold search.
- Per-dimension post-hoc calibrators (temperature, vector, isotonic, beta) are fitted
  on that split and stored as a JSON `CalibratorBundle` with a checksum, separately from
  model weights, carrying the backend id, prompt-contract hash, label-schema version,
  split name, dataset hash, and measured ECE before/after.
- A dimension with too few positives to fit is marked `degenerate` and abstains.
- With no bundle loaded the service returns **no probabilities** — only ordinal raw
  scores, and only on explicit request.

## Consequences

Deployments can and should refit calibration on representative traffic without touching
weights. A response's `CalibrationInfo` always states exactly what its numbers are.
