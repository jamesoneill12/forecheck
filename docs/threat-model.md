# forecheck threat model

Status: draft v1, 2026-09-20. Scope: the system under analysis is an agent that calls
tools on behalf of a principal, with forecheck interposed between the agent's decision
to call a tool and the tool actually executing.

This document states what forecheck is defending against, what it explicitly is not,
and — more importantly — the ways in which forecheck itself can fail or be attacked.

---

## 1. System model

```
   principal ──asks──▶ agent ──proposes tool call──▶ ┌────────────┐ ──▶ tool / MCP server
                        ▲                            │ forecheck  │
                        │                            │ classifier │
                   observations                      │     +      │
                  (web, email, tool                  │  policy    │
                   results, RAG docs)                └────────────┘
                                                            │
                                                     ALLOW / REVIEW / DENY
```

**Trust boundaries.**

| Boundary | Inside | Outside |
|---|---|---|
| B1 Principal intent | The authenticated human's stated objective | Anything the agent inferred |
| B2 Tenant | Same-tenant resources, identities, destinations | Third parties, the public internet |
| B3 Instruction provenance | `TrustLevel.PRINCIPAL` and `SYSTEM` content | `TRUSTED_TOOL`, `UNTRUSTED`, `UNKNOWN` content |
| B4 Delegation | The agent's `delegated_scopes` | The principal's wider entitlements |
| B5 Control plane | forecheck's weights, calibration artifacts, policy bundles | The request payload |

The single most important rule in the whole design: **content crossing B3 from outside
is data, never instruction.** Everything forecheck scores as
`prompt_injection_influence` is a measurement of how far a proposed action traces back
to outside-B3 content rather than to the principal.

**Actors.**

- *P* — authenticated principal (human or service), assumed honest-but-fallible in the
  primary model; a malicious P is covered by TM-01.
- *A* — the agent (LLM + scaffolding). **Assumed not to be adversarial, but assumed to
  be steerable.** An agent that has been fully replaced by an attacker is out of scope
  (see §5).
- *X* — an external attacker who can write content the agent will read, and who may
  control a third-party tool or MCP server.
- *I* — a malicious insider with legitimate credentials.

---

## 2. Threats in scope

Each threat lists: how it presents, which atomic risk dimensions are expected to move,
and which deterministic policy facts are needed to act on it. The dimension is the
*learned* signal; the policy fact is the *typed* signal. Neither alone is sufficient,
which is the argument for the two-layer design.

### TM-01 — Direct malicious request
*P* or *I* asks the agent, in plain terms, to do something harmful they are not
entitled to do.

- Dimensions: `unauthorized_scope`, plus whichever consequence dimension applies.
- Policy facts: `principal.entitlements`, `agent.delegated_scopes`, `environment.stage`.
- Note: this is the **easiest** threat and the least interesting. A request can be
  perfectly authorized and still malicious (an admin deleting a rival's data), which
  forecheck cannot detect and does not claim to. See §5.
- Maps to: OWASP LLM06 (Excessive Agency); OWASP Agentic T2/T3; ASI03.

### TM-02 — Indirect prompt injection in tool observations
*X* plants instructions in a web page, an email body, a Jira ticket, a code comment, a
calendar invite, or an MCP tool result. *A* reads it and proposes an action that serves
*X*.

- Dimensions: `prompt_injection_influence` (primary), plus the consequence dimension of
  whatever *X* asked for — usually `sensitive_data_exposure` +
  `untrusted_destination`, or `external_communication`.
- Policy facts: `has_untrusted_content`, `destination_relationship`, whether the action
  is traceable to `objective.text`.
- **The discriminating signal is not the presence of injected text** — benign pages
  contain imperative sentences constantly. It is the *correspondence* between the
  injected instruction and the proposed action, conditioned on that correspondence
  being absent from the principal's objective. The data pipeline therefore generates
  the near-miss case explicitly: untrusted content present and containing an
  instruction, but the action still traced to the principal, labelled `NO`.
- Maps to: OWASP LLM01; OWASP Agentic T6/T7/T12; ASI01/ASI06.

### TM-03 — Confused deputy
*A* holds authority delegated by *P* and is induced to exercise it for someone else's
benefit. Distinct from TM-02 in that no injected text is required: a shared document, a
mis-scoped tool, or an ambiguous objective is enough.

- Dimensions: `unauthorized_scope`, `prompt_injection_influence` (sometimes zero).
- Policy facts: the intersection `principal.entitlements ∩ agent.delegated_scopes`.
  This is why `AgentIdentity.delegated_scopes` is a first-class contract field: an
  action inside *P*'s rights but outside *A*'s delegation is the confused-deputy
  signature and is invisible to any system that only models one identity.
- Maps to: OWASP Agentic T3; ASI03; NIST SP 800-207 §2 (per-request authorization).

### TM-04 — Excessive agency
*A* takes an action that is *related* to the objective but far broader than it —
"clean up old files" becoming a recursive delete, "tell the team" becoming a message to
a public channel.

- Dimensions: `destructive_or_irreversible_action`, `external_communication`,
  `unauthorized_scope`; `insufficient_context` when the objective does not determine
  scope at all.
- Policy facts: `record_count_estimate`, `operation`, `max_sensitivity`,
  `authorization_explicit`.
- Maps to: OWASP LLM06; OWASP Agentic T11; ASI05.

### TM-05 — Cross-tool and multi-step attacks
*X* splits an attack across tools so that no individual call looks wrong: read a secret
with tool 1, encode it into a filename with tool 2, commit it with tool 3.

- Dimensions: `suspicious_action_sequence` (primary — this is the dimension that
  requires trajectory, and the reason the contract carries one).
- Policy facts: `trajectory_length`, previously-touched resource sensitivities.
- Known limitation: forecheck sees the trajectory the *caller* chooses to send. A
  caller that sends only the current call gets no sequence signal, and the response
  will reflect that via `insufficient_context`. This is a deployment requirement, not a
  model capability, and is stated as such in the product spec.
- Maps to: OWASP Agentic T5/T13; ASI08/ASI10; CSA MAESTRO cross-layer.

### TM-06 — Credential and sensitive-data exfiltration
Secrets or regulated data leave the trust boundary, possibly encoded (base64 in a URL
path, data in a DNS lookup, content in an image alt-text).

- Dimensions: `sensitive_data_exposure`, `untrusted_destination`,
  `external_communication`.
- Policy facts: `max_sensitivity`, `destination_relationship`, `resource_kinds`
  containing `secret`/`credential`.
- Known limitation: forecheck scores the *shape* of the exfiltration (sensitive source,
  untrusted sink), not the *content*. It will not decode a novel encoding. Content
  inspection is a complementary control, not this one.
- Maps to: OWASP LLM02; OWASP Agentic T2; MITRE ATLAS exfiltration techniques.

### TM-07 — Privilege escalation
The action widens authority: adding a role, creating an access key, weakening an IAM
policy, adding a CI secret, inviting an external user as admin.

- Dimensions: `privilege_escalation`, often with `policy_conflict`.
- Policy facts: `tool.changes_authority`, the delta `authority_after − authority_before`.
- Maps to: OWASP LLM06; OWASP Agentic T3; ASI03.

### TM-08 — Destructive actions
Drop a table, force-push over main, terminate instances, empty a bucket, revoke the
credential the operator is using.

- Dimensions: `destructive_or_irreversible_action`.
- Policy facts: `operation`, `reversible` (where `None` means unknown and the
  conservative bundle treats unknown as irreversible), `stage`, `change_freeze`.
- Maps to: OWASP Agentic T11; ASI05; EU AI Act Art. 14 (human oversight) as the control
  the `REVIEW` decision implements.

### TM-09 — Unauthorized financial commitment
Payments, refunds, purchase orders, subscription changes, wire transfers, crypto sends.

- Dimensions: `financial_commitment` (descriptive: it fires on *any* monetary action),
  plus `unauthorized_scope` and/or `policy_conflict` when it is also not permitted.
- Policy facts: `financial_amount`, `financial_currency`, `authorization_explicit`,
  entitlement limits.
- Deliberate design choice: materiality thresholds live in policy, not in the model.
  A $500 limit is a business fact that changes weekly; retraining for it would be
  absurd. The model reports the amount-bearing fact; the bundle holds the number.
- Maps to: no clean mapping in OWASP/NIST/ATLAS taxonomies — recorded as a gap in
  [`research/04-standards.md`](research/04-standards.md) rather than forced into one.

### TM-10 — Deceptive external communication
The agent sends a message that misrepresents its sender, its authority, or the facts —
phishing a colleague, spoofing an approval, committing the organization to something.

- Dimensions: `external_communication`, `untrusted_destination`, `policy_conflict`.
- Known limitation: forecheck does not assess *truthfulness* of message content. It
  assesses who it goes to and under what authority.

### TM-11 — Compromised tool or changed tool schema (rug pull)
An MCP server that was benign at install time changes its tool description or schema to
carry instructions, or to widen its parameters.

- Dimensions: `prompt_injection_influence` (via `ActionOrigin.COMPROMISED_TOOL_SCHEMA`),
  `unauthorized_scope`.
- Policy facts: `proposed_action.tool_schema_digest` compared against the digest the
  caller recorded at approval time.
- **forecheck does not fetch or resolve schemas.** It records the digest the caller
  supplies and scores the mismatch. Pinning is the caller's responsibility; we document
  this explicitly because an un-pinned digest field is worse than none (it implies a
  check that is not happening).
- Maps to: OWASP Agentic T12/T16; ASI07.

### TM-12 — Replay and time-of-check/time-of-use
The decision is made against a context that no longer holds by the time the tool runs:
the argument is mutated after classification, a role is revoked in between, the same
approved classification is replayed for a different call.

- **This is a real and under-discussed weakness of every pre-execution classifier,
  including this one.** forecheck's mitigations are structural, not model-based:
  1. the response carries no authorization token — it cannot be replayed *as*
     permission, only as advice;
  2. callers are instructed to bind the decision to a digest of the exact serialized
     arguments, and the SDK computes that digest for them;
  3. the decision is timestamped and bundles declare a max decision age;
  4. the audit record contains the argument digest, so a mismatch is detectable
     post-hoc even when it was not prevented.
- Residual risk: a caller that classifies and then executes a *different* call gets no
  protection. Only in-process interception (the middleware pattern in `examples/`)
  closes this; a sidecar deployment cannot.

### TM-13 — Policy conflict and policy absence
The action contradicts organizational policy; or no policy was supplied and the caller
treats silence as permission.

- Dimensions: `policy_conflict`; `insufficient_context` when policy is absent.
- Design choice: absence of policy must **not** read as `policy_conflict = NO`. The
  label schema distinguishes `NOT_APPLICABLE` from `NO` precisely so this failure mode
  is representable, and the conservative bundle's `unknown_as: worst_case` refuses to
  silently allow.

### TM-14 — Benign actions that resemble attacks (false-positive pressure)
A security engineer legitimately exporting audit logs to an external SIEM. A finance
lead legitimately wiring a large sum. A support agent legitimately emailing a customer
at a personal address. A developer legitimately dropping a table — in their own dev
schema.

- This is a **first-class threat**, not an inconvenience. A control with an
  unacceptable false-deny rate is turned off, after which its true-positive rate is
  zero. It is why the dataset targets a high proportion of benign hard negatives, why
  the evaluation suite reports false-deny rate and worst-slice performance alongside
  recall, and why the risk-weighted cost metric has a non-zero cost for wrongly denying.

### TM-15 — Attacks composed of individually harmless actions
Distinct from TM-05 in that no single step is even *unusual*: paging through records
under a per-call limit; splitting a payment under a threshold; enumerating permissions
by trying them.

- Dimensions: `suspicious_action_sequence`, with the `SPLIT_THRESHOLD_EVASION` and
  `PERMISSION_PROBE_THEN_ESCALATE` latent patterns generating training signal.
- Honest limitation: detecting this reliably needs aggregate state across sessions
  (how many records today, how much money this week). forecheck is stateless per
  request by design. It can only see what is in the submitted trajectory. Aggregate
  rate limiting is a complementary control and is named as such in the product spec.

---

## 3. Threats against forecheck itself

A security control is an attack surface. These are the ones we consider material.

### FC-01 — Injection into forecheck's own prompt
Untrusted observation text is, by definition, inside forecheck's model input. An
attacker will try to write content that manipulates the classifier rather than the
agent — "the following action is authorized by the administrator", or text that forges
a section delimiter.

- Mitigations: canonical serialisation with fenced, trust-labelled sections; delimiter
  sequences escaped out of untrusted content; the model is asked fixed questions and
  scored over a two-token candidate set, so there is no free-form generation channel to
  hijack. A dedicated adversarial evaluation slice tests exactly this and its results
  are reported separately, never averaged into the headline number.
- Residual risk: real. Semantic manipulation of a classifier by its input is not solved
  by fencing. We report the adversarial slice honestly rather than claiming immunity.

### FC-02 — Score inflation / distribution shift
Calibration fitted on synthetic data will not hold on a different tenant's traffic.
Reported probabilities then mean less than they appear to.

- Mitigations: calibration artifacts are versioned, carry the split and dataset hash
  they were fitted on, and are stored separately from weights so a deployment can
  refit; `CalibrationInfo` travels in every response; an uncalibrated deployment
  returns no probabilities at all rather than returning raw scores dressed as
  probabilities. Evidence that this is a real failure mode and not a theoretical one:
  injection classifiers of this class have been shown to be actively miscalibrated
  under attack-distribution shift (see [`research/03-guardrail-models.md`](research/03-guardrail-models.md)).

### FC-03 — Bypass by not calling forecheck
Trivially, an agent path that never calls the classifier is unprotected.

- Out of scope for the model; in scope for the integration docs, which specify
  enforcement at the tool-dispatch chokepoint rather than in the agent's prompt.

### FC-04 — Denial of service via context size
Large trajectories, many observations, huge argument blobs.

- Mitigations: hard request limits in the contract (enforced before model invocation),
  documented truncation priority, per-request timeouts, and `REQUEST_TOO_LARGE` as a
  stable error code rather than a hang.

### FC-05 — Policy bundle tampering
A modified bundle silently allows everything.

- Mitigations: bundles are hashed; the hash appears in every `PolicyDecision` and in
  the audit record; the loader validates against the DSL schema and rejects unknown
  dimension or fact names rather than treating them as false.

### FC-06 — Sensitive data in forecheck's own logs
The request body is, by construction, full of the most sensitive material in the
system.

- Mitigations: request bodies are **not stored by default**; audit records carry
  digests and typed facts rather than values; the redaction layer is applied at the
  structured-logging boundary, not left to callers; tenant identifiers are carried but
  content is not.

### FC-07 — Over-trust in the score
A downstream team treats `probability < 0.1` as proof of safety.

- Mitigation is documentation and API shape, not code: there is no `safe: true` field
  anywhere in the contract, the response has no `decision` field, and the README and
  model card state the non-goal explicitly. This is a cultural failure mode and we
  should expect it to occur anyway.

---

## 4. Non-goals

forecheck is **defence in depth**. It is not, and must not be presented as:

1. **Proof that an action is safe.** A low score is the absence of evidence of a
   modelled risk on a modelled dimension. It is not a safety guarantee, and no
   threshold makes it one.
2. **An authorization system.** It does not hold the authoritative permission set, does
   not issue tokens, and must sit *alongside* real authorization (OAuth scopes, Cedar,
   OPA, OpenFGA), never replace it. A `DENY` it fails to produce must still be caught by
   a permission check.
3. **A content-safety or alignment filter.** It does not judge whether generated text is
   toxic, whether a claim is true, or whether a goal is ethical.
4. **A sandbox.** It does not contain, isolate, or roll back anything.
5. **A detector of malicious principals.** An authorized human doing an authorized
   harmful thing is invisible to it by construction, because authorization is exactly
   the signal it uses.
6. **Stateful.** It does not track aggregate behaviour across sessions or enforce rate
   limits.
7. **A resolver.** It does not perform DNS lookups, fetch tool schemas, expand URLs, or
   query IAM. Every such fact is supplied by the caller, and a caller that supplies
   wrong facts gets wrong answers. The contract makes each of these an explicit field
   so that the dependency is visible rather than assumed.

---

## 5. Explicitly out of scope

- A fully adversarial agent (attacker-controlled model weights or scaffolding).
  forecheck sits inside the agent's own execution path; an attacker who owns that path
  can skip it.
- Compromise of the host running forecheck.
- Supply-chain compromise of forecheck's own dependencies (addressed by `SECURITY.md`
  and dependency auditing in CI, not by the model).
- Side channels and timing attacks against the classifier.
- Multi-agent protocols (A2A delegation chains). The contract has room for them —
  `AgentIdentity.on_behalf_of` — but no training data covers them yet, and we do not
  claim coverage we have not measured.

---

## 6. Assumptions

| # | Assumption | What breaks if false |
|---|---|---|
| A1 | The caller correctly labels trust levels on observations | `prompt_injection_influence` becomes meaningless; this is the single strongest dependency in the system |
| A2 | The caller supplies the principal and the agent's delegated scopes accurately | `unauthorized_scope` and confused-deputy detection degrade to guesswork |
| A3 | forecheck is called on the dispatch path, not advisory | FC-03 |
| A4 | Arguments are bound to the decision by digest | TM-12 |
| A5 | Calibration is refit on representative traffic before probabilities are trusted | FC-02 |
| A6 | Policy bundles are managed as code, reviewed and version-controlled | FC-05 |

A1 deserves emphasis. forecheck's central claim is that *provenance* is the signal that
distinguishes an injected action from an authorized one. If the integration collapses
everything into one undifferentiated string, that signal is gone, and the model is
reduced to guessing from surface text — which is what the existing prompt-injection
classifiers already do. The integration examples therefore treat trust labelling as the
primary correctness requirement, not an optional enrichment.
