# ADR 0007 — Policy bundles are declarative YAML with no embedded code

Status: accepted, 2026-09-20

## Context

Rego, Cedar and Python plug-ins are all more expressive than we need, and every one of
them can hide I/O, nondeterminism or an unbounded loop inside a policy. The policy
engine's value is that an auditor can read it.

## Decision

A small YAML grammar: `all` / `any` / `not`, a `score` predicate over a named
`RiskDimension` with a threshold, and a `fact` predicate over a registered typed context
fact. Unknown dimension or fact names are load errors. Rules carry `decision`, `hard`,
and `obligations`. Combination is most-restrictive-wins. Bundles declare
`default_decision`, `uncalibrated_decision`, `allow_uncalibrated` and `unknown_as`.

Nothing in a bundle may name a tool without also naming a context fact; "this tool is
always denied" is precisely the mistake the whole design exists to avoid.

## Consequences

Organizations that already run OPA or Cedar can call forecheck for scores and keep their
own decision layer; the shipped engine is a reference implementation of the contract,
not a mandatory component.
