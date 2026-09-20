# forecheck product specification

Version 1.0 of the contract. Status: draft, pre-alpha. The wire schema is implemented
in `src/forecheck/contracts/` and that code is authoritative; this document explains
intent and the rules the code cannot express.

---

## 1. What forecheck is

A pre-execution risk classifier for AI-agent tool calls, plus a deterministic policy
engine.

**One call in, typed numbers out.** The caller submits everything it knows about a
proposed tool call. forecheck returns a calibrated probability for each of eleven
atomic risk dimensions. It does not return prose, a rationale, a chain of thought, or a
decision.

**A second, separate call turns numbers into a decision.** `/v1/policies/evaluate`
applies a versioned, hashed, declarative policy bundle to those scores plus typed
context facts, and returns `ALLOW`, `REVIEW` or `DENY` together with the exact rules
that fired.

The two layers are separate because they change on different schedules for different
reasons. Risk facts are properties of the world and change when the threat landscape
changes. Decisions are properties of a business and change when a finance lead raises a
limit. Coupling them means retraining a model to change a number, and it means an
auditor cannot read why an action was blocked.

## 2. Who it is for

- Platform teams running agents that call real tools in an enterprise.
- MCP gateway and agent-framework authors who need a risk signal to gate on.
- Security teams who need an auditable record of why an agent action was permitted.

It is not for end users, and it is not a chat safety filter.

## 3. The eleven dimensions

| Dimension | Asks | Descriptive, not normative |
|---|---|---|
| `prompt_injection_influence` | Does this action trace to untrusted content rather than the principal? | — |
| `unauthorized_scope` | Is it outside the principal's entitlements narrowed by the agent's delegation? | — |
| `sensitive_data_exposure` | Does it move data to a sink less trusted than the source? | — |
| `untrusted_destination` | Is the destination external, unknown, or a look-alike? | — |
| `privilege_escalation` | Does it widen authority? | — |
| `destructive_or_irreversible_action` | Can it be undone? | A routine `DELETE` scores high and may still be allowed |
| `financial_commitment` | Does it create a monetary obligation? | Payroll scores high |
| `external_communication` | Does it message outside the boundary? | Emailing a customer scores high |
| `policy_conflict` | Does it contradict a supplied policy statement? | — |
| `suspicious_action_sequence` | Does the trajectory form an attack shape? | — |
| `insufficient_context` | Is the supplied context inadequate to determine the rest? | The abstention channel |

The middle column is why the model must never be taught that a neutral action is always
allowed or always denied. `financial_commitment = 0.99` on a payroll run is *correct*.
Turning that into a block is the policy engine's job, using `authorization_explicit`,
the principal's entitlement limits and the amount.

## 4. Request contract

`POST /v1/classify`, body `ClassifyRequest`. The full field list is in
`src/forecheck/contracts/context.py`; the parts that carry obligations:

**Required.** `objective`, `principal`, `agent`, `proposed_action`.

**Strongly recommended, and named in the response when missing.** `observations` with
honest `trust` labels; `trajectory`; `resources` with `sensitivity` and `reversible`;
`destination` with `relationship`; `policies`; `environment.stage`.

**Caller obligations.** These are the assumptions the model's accuracy rests on, and
they are the caller's responsibility, not forecheck's:

1. *Label trust honestly.* Any content the agent read from outside the trust boundary
   is `TrustLevel.UNTRUSTED`, including tool results. Collapsing everything to
   `UNKNOWN` destroys the primary injection signal.
2. *Set `authorization_explicit` only when it is true.* Inferring authorization from a
   broad objective must leave it `false`. A caller that sets it `true` by default has
   disabled a large part of the system.
3. *Supply `delegated_scopes` separately from `entitlements`.* They are different sets
   and their difference is what detects confused-deputy behaviour.
4. *Pin `tool_schema_digest` at approval time and resend it.* forecheck records it; it
   does not fetch it.
5. *Bind the decision to the arguments.* Compute a digest over the exact serialized
   arguments you will execute and carry it into your audit record. The SDK does this.

**Limits** (`contracts/limits.py`): 1 MiB request, 64 trajectory steps, 64
observations, 64 resources, 64 policy statements, 32 items per batch, 8192 prompt
tokens. Exceeding them yields a typed error, never a truncated silent success — except
context length, which truncates in a documented priority order and reports it in
`TruncationInfo`.

## 5. Response contract

`ClassifyResponse` carries `scores`, `model`, `calibration`, `truncation`,
`abstained`, `abstention_reasons`, `latency_ms`. It deliberately has **no `decision`
field and no `safe` field.**

### 5.1 The calibration rule

This is the contract's central honesty guarantee:

- If no calibration artifact is loaded, `calibration.method == "none"`, every
  `DimensionScore.probability` is `null`, and `calibrated` is `false`. Raw scores are
  returned **only** when the caller sets `options.include_uncalibrated`, and they are
  ordinal — comparable within a dimension, not across dimensions, and not
  interpretable as frequencies.
- If an artifact is loaded, it was fitted on a dedicated calibration split used for
  nothing else, and `CalibrationInfo` reports the method, the split, the fitting set
  size, the dataset hash and the measured ECE.
- A softmax output is never described as a probability anywhere in this project.

### 5.2 Abstention

Abstention is first class at two levels. Per dimension: `abstained: true` with a null
probability, used when the calibrator for that dimension was degenerate (too few
positives to fit) or the predictive interval is too wide. Per response:
`abstained: true` with `abstention_reasons`, used on truncation, timeout, or a high
`insufficient_context` score.

An abstained dimension is **not** a zero. Policy bundles declare `unknown_as` and the
conservative default is `worst_case`.

### 5.3 Errors

Stable `ErrorCode` enum in the body; HTTP status is advisory. `retryable` is set by the
server so clients do not have to maintain their own table. Error details carry a
`field_path` but never a field *value*, because the error path is the most-logged path
and request bodies contain secrets.

## 6. Policy contract

`POST /v1/policies/evaluate` accepts either a `ClassifyResponse` (caller already
classified) or an `ActionContext` (classify then evaluate) — exactly one, so the
provenance of the scores is never ambiguous.

Guarantees:

- **Pure and total.** No I/O, no model, no randomness. Same input, same output.
- **Fail closed.** No rule matching yields the bundle's `default_decision`.
- **Most-restrictive-wins.** `DENY` > `REVIEW` > `ALLOW`; nothing cancels a `DENY`
  from a rule marked `hard`.
- **Uncalibrated input.** Probability thresholds do not silently apply to raw scores.
  Either the bundle opts in explicitly, or evaluation returns `uncalibrated_decision`.
- **Replayable.** `matched_rules` reproduces the decision, with the actual fact values
  and thresholds that fired.
- **Hashed.** `policy_bundle_hash` ties a decision to an exact bundle version in the
  audit record.

Three bundles ship: `conservative`, `balanced`, `permissive`. None of them deny on tool
name alone.

## 7. Versioning

| Version | Covers | Bump rule |
|---|---|---|
| `schema_version` | Wire contract | Additive field → minor; removal/rename/semantic change → major |
| `label_schema_version` | The eleven dimensions and `LabelValue` | Any change invalidates calibration artifacts, which refuse to load |
| `prompt_contract_hash` | Serialization + question text + field order | Any change invalidates checkpoints; the classifier refuses a mismatched bundle |
| `policy_dsl_version` | Bundle grammar | Loader rejects unknown versions |
| `model.revision` | Weights / adapter | Free |

A calibration artifact whose `prompt_contract_hash` or `label_schema_version` does not
match the running code raises at load time. It does not warn and continue.

## 8. Performance targets

Targets, not measurements. Nothing here is claimed as achieved; measured numbers go in
the model card with the hardware named.

| Backend | Target p50 | Target p99 |
|---|---|---|
| Mock (policy path only) | < 2 ms | < 10 ms |
| ~1B on a single modern GPU | < 25 ms | < 60 ms |
| ~4B on a single modern GPU | < 60 ms | < 150 ms |
| ~8-9B on a single modern GPU | < 120 ms | < 300 ms |
| ~1B on CPU | < 400 ms | < 1200 ms |

Scoring eleven dimensions with one shared context prefill is the mechanism that makes
these plausible: the context is encoded once and each dimension costs one short
question plus a two-token logit read.

## 9. Deployment shapes

1. **In-process middleware** — wraps the tool dispatcher. The only shape that closes
   the time-of-check/time-of-use gap (TM-12), because the arguments classified are the
   arguments executed.
2. **Sidecar HTTP service** — language-agnostic, but the caller must bind arguments to
   the decision by digest itself.
3. **MCP interceptor** — sits in the gateway between client and MCP servers.

## 10. Out of scope

Restated from the threat model because it belongs in the product boundary too:
forecheck is not an authorization system, not a sandbox, not a content filter, not
stateful, and not a resolver. It does not prove an action is safe. Everything it knows,
the caller told it.
