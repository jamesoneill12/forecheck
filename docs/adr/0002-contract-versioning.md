# ADR 0002 — Four independent version axes, each with a hard failure mode

Status: accepted, 2026-09-20

## Context

A checkpoint trained under one prompt serialization and served under another produces
plausible-looking garbage. A calibration artifact fitted against one label schema and
applied to another does the same. Neither failure is visible in the output.

## Decision

Four version identifiers, each independently checked:

| Axis | Identifier | On mismatch |
|---|---|---|
| Wire schema | `schema_version` | 400 `unsupported_schema_version` |
| Label schema | `label_schema_version` | calibration artifact refuses to load |
| Prompt contract | `prompt_contract_hash` (sha256 of template + questions + field order) | classifier refuses a mismatched calibration bundle |
| Policy DSL | `dsl_version` | loader rejects the bundle |

Every `ClassifyResponse` carries the prompt-contract hash and every `PolicyDecision`
carries the bundle hash, so an audit log entry is sufficient to reproduce the decision.

## Consequences

Mismatches raise; they never warn-and-continue. Enum additions are minor bumps;
removals or semantic changes are major bumps and invalidate artifacts.
