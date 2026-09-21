# forecheck product specification

Version 1.0 of the contract. Status: draft, pre-alpha. The wire schema is implemented
in `src/forecheck/contracts/` and that code is authoritative; this document explains
intent and the rules the code cannot express.

---

## 1. What forecheck is for

forecheck is a pre-execution risk model plus a deterministic policy engine for AI-agent
tool calls (full mechanism in §5 onward). The mechanism is not the product story. The
product story is four things a platform team can point at a dashboard and say:

1. **Approvals eliminated at a fixed incident rate.** Every `REVIEW` decision is a human
   in the loop, and every human in the loop is the thing blocking agent rollout at
   scale. forecheck's calibration and abstention machinery let a deployment convert a
   stated fraction of its `REVIEW` queue into confident automatic `ALLOW`/`DENY`, and
   report exactly what incident rate that conversion costs. See
   `docs/evaluation/approval-elimination.md` for the precise definition and the curve.
2. **Delegated-authority conformance.** Most "is this agent action safe" questions are
   actually "was this agent authorized, by this principal, for this task, to do this" —
   a scope question, not a content question. forecheck already carries the fields this
   needs: `Principal.entitlements` (what the human can do),
   `AgentIdentity.delegated_scopes` (what was actually handed to the agent for this
   task), and `AgentIdentity.on_behalf_of` (delegation chains). The
   `unauthorized_scope` dimension and the confused-deputy detection in
   `docs/threat-model.md` TM-03 are built on the *difference* between those two sets,
   which is invisible to any system that models only one identity.
4. **The label flywheel.** Every human approval, rejection, modification, escalation or
   expiry on a `REVIEW` is a label on a real action. `POST /v1/feedback` (§6) captures
   it. This is how calibration and policy thresholds move from synthetic data to a
   customer's real traffic, and it is the only path to a real (class-3) accuracy claim
   — see `docs/evaluation-plan.md` §1 and §6.
3. **Multi-policy composition without over-conservatism.** Real deployments run more
   than one policy source at once — an org-wide bundle, a per-tenant override, a
   per-tool restriction — and naive composition (deny-wins-everywhere) degrades to
   near-permanent `REVIEW` as sources multiply. A separate evaluation effort is
   building the composition metric for this; it is not yet part of this spec. The
   policy engine's `RuleKind.ALLOW_OVERRIDE` / `hard` mechanism (§6) is the primitive
   that composition will be built on, not the composition guarantee itself.

## 2. What we are not

- **Not a prompt-injection detector.** `prompt_injection_influence` is one of eleven
  descriptive dimensions, scored from typed provenance fields the caller supplies, not
  from reading text for injected imperatives. If the caller wants a dedicated,
  text-only injection classifier, that is a different product (e.g. a DeBERTa-class
  detector, referenced as a baseline in `docs/evaluation-plan.md` §4).
- **Not a content-safety or alignment filter.** forecheck does not judge whether
  generated text is toxic, hateful, or harmful to read. That space already has strong,
  purpose-built models — Prompt Guard 2, Llama Guard 4, Granite Guardian, ShieldGemma —
  and forecheck is not attempting to replace or beat them. It answers a different
  question: not "is this text unsafe to say", but "is this *action*, from this
  principal, under this delegation, safe to *execute*". A deployment that needs both
  runs both.
- **Not an authorization system, a sandbox, or a resolver.** Restated in full in
  `docs/threat-model.md` §4; the short version is in §11 below.

## 3. Who it is for

- **Buyer: a platform or security team deploying agents that call real tools.** Their
  pain is not "our agent said something bad" — content-safety tooling already exists
  for that. Their pain is **approval fatigue**: every mutating or external agent action
  routes to a human queue, the queue is the bottleneck on rolling agents out past a
  pilot, and nobody wants to be the person who removed the human step and got it wrong.
  Their KPI is **approvals eliminated at a fixed incident rate** — a number they can
  defend to their own security leadership, move deliberately, and watch in production
  via the feedback flywheel (§1.3) rather than trust once and forget.
- MCP gateway and agent-framework authors who need a risk signal to gate on.
- Security teams who need an auditable record of why an agent action was permitted, and
  a mechanism (§1.2) that detects an agent exceeding what it was actually delegated,
  not just what its principal could theoretically do.

It is not for end users, and — restating §2 — it is not a chat safety filter.

## 4. Honesty about where the numbers stand

Every dimension-level and decision-level number this project has produced so far is on
synthetic data (`docs/evaluation-plan.md` §1). There is no human-labelled gold set yet
and no production traffic. The approval-elimination curve in
`docs/evaluation/approval-elimination.md` is fully specified but not yet computable
end-to-end from real outcomes, because real outcomes do not exist until the feedback
flywheel (§1.3, §6) has run against live traffic. This document does not claim a real
approval-reduction number anywhere, and neither should anyone quoting it.

## 5. The eleven dimensions

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

## 6. Request contract

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
   and their difference is what detects confused-deputy behaviour and powers §1.2.
4. *Pin `tool_schema_digest` at approval time and resend it.* forecheck records it; it
   does not fetch it.
5. *Bind the decision to the arguments.* Compute a digest over the exact serialized
   arguments you will execute and carry it into your audit record. The SDK does this.

**Limits** (`contracts/limits.py`): 1 MiB request, 64 trajectory steps, 64
observations, 64 resources, 64 policy statements, 32 items per batch, 8192 prompt
tokens. Exceeding them yields a typed error, never a truncated silent success — except
context length, which truncates in a documented priority order and reports it in
`TruncationInfo`.

## 7. Response contract

`ClassifyResponse` carries `scores`, `model`, `calibration`, `truncation`,
`abstained`, `abstention_reasons`, `latency_ms`. It deliberately has **no `decision`
field and no `safe` field.**

### 7.1 The calibration rule

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

### 7.2 Abstention

Abstention is first class at two levels. Per dimension: `abstained: true` with a null
probability, used when the calibrator for that dimension was degenerate (too few
positives to fit) or the predictive interval is too wide. Per response:
`abstained: true` with `abstention_reasons`, used on truncation, timeout, or a high
`insufficient_context` score.

An abstained dimension is **not** a zero. Policy bundles declare `unknown_as` and the
conservative default is `worst_case`.

### 7.3 Errors

Stable `ErrorCode` enum in the body; HTTP status is advisory. `retryable` is set by the
server so clients do not have to maintain their own table. Error details carry a
`field_path` but never a field *value*, because the error path is the most-logged path
and request bodies contain secrets.

## 8. Policy contract

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

## 9. Feedback contract

`POST /v1/feedback` (`FeedbackRecord` / `FeedbackAck` in `contracts/io.py`) is how §1.3
actually gets fed: a request id, the decision forecheck returned, a human outcome
(`approved`/`rejected`/`modified`/`escalated`/`expired`), optionally corrected
per-dimension labels, a reviewer *role* (never a personal identifier — feedback exists
to refit calibration and thresholds in aggregate, not to build a per-person audit
trail), a free-text reason capped at 1024 characters, and the policy bundle and
calibration versions the original decision was made under. The default sink is a
pluggable append-only JSONL store; `forecheck feedback export` reads it back. Feedback
never changes a past decision — it only produces labels for the next calibration fit.

## 10. Versioning

| Version | Covers | Bump rule |
|---|---|---|
| `schema_version` | Wire contract | Additive field → minor; removal/rename/semantic change → major |
| `label_schema_version` | The eleven dimensions and `LabelValue` | Any change invalidates calibration artifacts, which refuse to load |
| `prompt_contract_hash` | Serialization + question text + field order | Any change invalidates checkpoints; the classifier refuses a mismatched bundle |
| `policy_dsl_version` | Bundle grammar | Loader rejects unknown versions |
| `model.revision` | Weights / adapter | Free |

A calibration artifact whose `prompt_contract_hash` or `label_schema_version` does not
match the running code raises at load time. It does not warn and continue.

## 11. Performance targets

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

## 12. Deployment shapes

1. **In-process middleware** — wraps the tool dispatcher. The only shape that closes
   the time-of-check/time-of-use gap (TM-12), because the arguments classified are the
   arguments executed.
2. **Sidecar HTTP service** — language-agnostic, but the caller must bind arguments to
   the decision by digest itself.
3. **MCP interceptor** — sits in the gateway between client and MCP servers.

## 13. Out of scope

Restated from the threat model because it belongs in the product boundary too:
forecheck is not an authorization system, not a sandbox, not a content filter, not
stateful, and not a resolver. It does not prove an action is safe. Everything it knows,
the caller told it.
