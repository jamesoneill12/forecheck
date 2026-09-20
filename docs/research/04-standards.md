# 04 — Standards, Taxonomies & Government/Industry Guidance

Scan date: 2026-09-20. Primary-source only (owasp.org / genai.owasp.org, nist.gov / csrc.nist.gov / nccoe.nist.gov, atlas.mitre.org / mitre.org, cloudsecurityalliance.org, eur-lex.europa.eu, datatracker.ietf.org, modelcontextprotocol.io, a2a-protocol.org, w3.org, spiffe.io). Every claim below was fetched by one of four parallel research passes; items that could not be independently confirmed from a primary page are explicitly flagged **[secondary-sourced]** or **NOT FOUND**. No ID, title, or date below was invented.

---

## 1. OWASP

### 1.1 OWASP Top 10 for LLM Applications 2025
- **Title:** OWASP Top 10 for LLM Applications 2025
- **Publisher:** OWASP (Top 10 for LLM Applications project, under OWASP GenAI Security Project)
- **Version / date:** "Version 2025", released 2024-11-18 (history: v1.0 2023-08-01, v1.1 2023-10-16)
- **URL:** https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/ (PDF: https://genai.owasp.org/download/43299/)
- **IDs (verbatim):**
  - LLM01:2025 Prompt Injection
  - LLM02:2025 Sensitive Information Disclosure
  - LLM03:2025 Supply Chain
  - LLM04:2025 Data and Model Poisoning
  - LLM05:2025 Improper Output Handling
  - LLM06:2025 Excessive Agency
  - LLM07:2025 System Prompt Leakage
  - LLM08:2025 Vector and Embedding Weaknesses
  - LLM09:2025 Misinformation
  - LLM10:2025 Unbounded Consumption
- **Actionable:** LLM06 (Excessive Agency) is the closest existing ID to "should this tool call run autonomously" — direct grounding for our `unauthorized_scope` / `privilege_escalation` dimensions. LLM01/LLM05 motivate treating any tool-call argument derived from untrusted upstream content (tool output, retrieved doc, email body) as tainted and subject to REVIEW. LLM10 grounds cost/rate-based DENY thresholds.

### 1.2 Agentic AI – Threats and Mitigations (OWASP Agentic Security Initiative)
- **Title:** "Agentic AI – Threats and Mitigations"
- **Publisher:** OWASP Agentic Security Initiative (OWASP GenAI Security Project)
- **Version / date:** v1.1, December 2025 (supersedes v1.0, 2025-02-17, which only defined T1–T15; the taxonomy grew to **T1–T17** in v1.1)
- **URL:** https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/ (PDF: https://genai.owasp.org/download/45674/)
- **T1–T17 (verbatim):**
  - T1 Memory Poisoning
  - T2 Tool Misuse
  - T3 Privilege Compromise
  - T4 Resource Overload
  - T5 Cascading Hallucination Attacks
  - T6 Intent Breaking & Goal Manipulation
  - T7 Misaligned & Deceptive Behaviors
  - T8 Repudiation & Untraceability
  - T9 Identity Spoofing & Impersonation / Agent Identity Compromise
  - T10 Overwhelming Human in the Loop
  - T11 Unexpected RCE and Code Attacks
  - T12 Agent Communication Poisoning
  - T13 Rogue Agents in Multi-Agent Systems
  - T14 Human Attacks on Multi-Agent Systems
  - T15 Human Manipulation
  - T16 Insecure Inter-Agent Protocol Abuse
  - T17 Supply Chain Compromise
- **Actionable:** each Txx ships a concrete mitigation list directly usable as policy-engine rules — e.g. T2 Tool Misuse → pre-execution validation, tool rate-limiting, execution logs for anomaly detection (= our pre-execution classifier's job description verbatim); T11 Unexpected RCE → sandbox execution + mandatory human review for AI-generated code requesting elevated privileges; T3 Privilege Compromise → granular permission controls, block cross-agent privilege delegation absent explicit grant.

### 1.3 Securing Agentic Applications Guide
- **Title:** Securing Agentic Applications Guide
- **Publisher:** OWASP GenAI Security Project — Agentic Security Initiative
- **Version / date:** 1.0, 2025-07-28 (Released)
- **URL:** https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/ (PDF: https://genai.owasp.org/download/49059/)
- **Structure:** Secure Agentic Architectures (Key Components KC1–KC6, attack-surface analysis) → Developer Guidelines across the lifecycle (design/build/runtime) → Enhanced Security Actions for single-agent / orchestrated multi-agent / swarm topologies → Key Operational Capabilities (API access, code execution, web use, filesystem/OS commands, critical-systems/SCADA) → Supply Chain → Assurance (red teaming, behavioral testing) → Runtime Hardening (containment, memory/tool/context security, observability + forensics).
- **Actionable:** §3.3 (Secure Operations & Runtime) and §9 (Runtime Hardening / Observability+Forensics) are the direct source for our pre-execution gating and logging requirements, keyed to KC5 (tool integration) and KC6 (operational environment/destination class).

### 1.4 OWASP "Agentic AI Top 10"
**NOT FOUND under that exact name.** Searches: `OWASP "Agentic AI Top 10"`; direct fetch of the Agentic Security Initiative page. What exists instead, under a different title:

- **Title:** OWASP Top 10 For Agentic Applications 2026
- **Publisher:** OWASP GenAI Security Project — Agentic Security Initiative
- **Version / date:** Version 2026, December 2025 (announced 2025-12-09)
- **URL:** https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ (PDF: https://genai.owasp.org/download/52117/)
- **ASI01–ASI10 (verbatim):**
  - ASI01 Agent Goal Hijack
  - ASI02 Tool Misuse and Exploitation
  - ASI03 Identity and Privilege Abuse
  - ASI04 Agentic Supply Chain Vulnerabilities
  - ASI05 Unexpected Code Execution (RCE)
  - ASI06 Memory & Context Poisoning
  - ASI07 Insecure Inter-Agent Communication
  - ASI08 Cascading Failures
  - ASI09 Human-Agent Trust Exploitation
  - ASI10 Rogue Agents
- **Actionable — highest-value single document found in this scan:** ASI02 prescribes a "Policy Enforcement Middleware ('Intent Gate')" — a pre-execution Policy Enforcement Point / Policy Decision Point that validates intent and arguments, enforces schemas and rate limits, and issues short-lived credentials. This is the closest primary-source blueprint for exactly what we're building. Each ASI entry is explicitly cross-mapped by OWASP itself to LLM01–LLM10 and to T1–T17 (e.g. ASI01 = T6+T7; ASI02 = T2, contributing T4/T16) — we reuse those OWASP-authored cross-mappings in §7 below rather than re-deriving them.

### 1.5 OWASP GenAI Security Project — outputs
- **URL:** https://genai.owasp.org/initiatives/
- 8 active initiatives: Top 10 for LLM and GenAI; Agentic App Security (Agentic Security Initiative); AI Red Teaming; AI Security Solutions Landscape; AI Bill of Materials (AIBOM); Secure Governance; Threat Intelligence; Data Security.
- Additional standalone outputs (via https://genai.owasp.org/resources/): "State of Agentic AI Security and Governance"; "Agent Control Standard (ACS)"; "A Practical Guide for Secure MCP Server Development" (Feb 2026); "AI Security Solutions Landscape for Agentic AI Q2 2026"; "AIUC-1: Crosswalks OWASP Top 10 For Agentic Applications" (May 2026).

---

## 2. NIST

### 2.1 NIST AI 100-2e2025 — Adversarial Machine Learning Taxonomy
- **Title:** Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations
- **Publisher:** NIST (Trustworthy and Responsible AI report series)
- **Version / date:** NIST AI 100-2 **E2025** (revision of AI 100-2e2023), March 2025
- **URL:** https://csrc.nist.gov/pubs/ai/100/2/e2025/final (DOI 10.6028/NIST.AI.100-2e2025)
- **Top-level categories confirmed:**
  - Predictive AI (PredAI): Evasion, Poisoning, Privacy
  - Generative AI (GenAI): Evasion, Poisoning, Privacy, **Misuse/Abuse** (new in the 2025 edition)
- **Caveat:** numbered sub-technique IDs (fine-grained, e.g. attack-family codes) could not be extracted from the fetched HTML/text; only the category names above are primary-verified. Indirect prompt injection is explicitly named as a 2025-edition addition under GenAI Misuse/Abuse.
- **Actionable:** gives a citable, government-sourced 4-category "why" taxonomy (Evasion / Poisoning / Privacy / Misuse-Abuse) usable as a top-level tag on any DENY/REVIEW decision.

### 2.2 NIST AI RMF 1.0 + Generative AI Profile (AI 600-1)
- **AI RMF 1.0** — NIST AI 100-1, 2023-01-26, https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf. Core functions: **GOVERN, MAP, MEASURE, MANAGE**.
- **Generative AI Profile** — NIST AI 600-1, 2024-07-26, https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf (DOI 10.6028/NIST.AI.600-1). 12 named risks: CBRN Information/Capabilities; **Confabulation**; Dangerous/Violent/Hateful Content; Data Privacy; Environmental Impacts; Harmful Bias & Homogenization; Human-AI Configuration; Information Integrity; **Information Security**; Intellectual Property; Obscene/Degrading Content; **Value Chain and Component Integration**. (List corroborated via NIST's own announcement + secondary summary; the PDF body's ~400 suggested actions were not independently re-extracted — flag if per-action citation is ever needed.)
- **Actionable:** Value Chain and Component Integration is the cleanest existing NIST risk name for third-party tool/plugin/MCP-server risk. Information Security and Confabulation ground DENY/REVIEW triggers respectively for (a) actions weakening security posture and (b) actions executing on a hallucinated premise → direct tie to our `insufficient_context` dimension. Human-AI Configuration is NIST's term for human-in-the-loop design, i.e. the justification for our REVIEW tier. GOVERN/MAP/MEASURE/MANAGE gives the lifecycle skeleton: GOVERN = our ALLOW/REVIEW/DENY policy definitions, MAP = per-call risk/context identification, MEASURE = logging/telemetry, MANAGE = incident response on DENY-bypass or REVIEW escalation.

### 2.3 COSAIS — Control Overlays for Securing AI Systems
- **Project:** NIST SP 800-53 Control Overlays for Securing AI Systems. Concept paper 2025-08-14; project created 2025-07-10; annotated outline "Using and Fine-Tuning Predictive AI" 2026-01-08 (discussion draft).
- **URLs:** project https://csrc.nist.gov/projects/cosais; concept paper https://csrc.nist.gov/csrc/media/Projects/cosais/documents/NIST-Overlays-SecuringAI-concept-paper.pdf; predictive-AI outline https://csrc.nist.gov/csrc/media/Projects/cosais/documents/COSAiS-Predictive-AI-annotated-outline-Jan2026.pdf
- Planned NISTIR series: **8605** (overview/methodology), **8605A** (predictive AI — the only one with drafted content so far), **8605B** (generative AI). Two agent use cases are scoped on the project's use-case list (https://csrc.nist.gov/Projects/cosais/use-cases) — "Using AI Agent Systems (Single Agent)" and "(Multi-Agent)" — but **no control mappings for these have been published as of 2026-09-20**; agentic overlays are on a late-2026/2027 timeline.
- **Actionable:** cite as "NIST is developing agent-specific SP 800-53 overlays" — do NOT borrow specific control IDs for agent tool-calls from COSAIS yet; nothing agent-specific is published.

### 2.4 2025–2026 NIST agentic-AI-specific work
- **AI Agent Standards Initiative** — NIST CAISI, announced 2026-02-17. https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure — three pillars: industry-led standards / US leadership in international bodies; community-led open-source agent protocol work; agent security & identity research.
- **CAISI RFI on securing AI agent systems** — Federal Register notice, opened 2026-01-08, comments closed 2026-03-09. https://www.nist.gov/news-events/news/2026/01/caisi-issues-request-information-about-securing-ai-agent-systems
- **NCCoE concept paper** — "Accelerating the Adoption of Software and AI Agent Identity and Authorization," comment deadline 2026-04-02. https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf (project: https://www.nccoe.nist.gov/projects/software-and-ai-agent-identity-and-authorization)
- No finalized NIST Special Publication titled "Agentic AI Security" exists yet (consistent with the COSAIS timeline). **Actionable:** cite these as evidence the pre-execution-authorization problem is a live, NIST-acknowledged gap our classifier fills — not evidence we're implementing an existing finalized NIST control set.

### 2.5 NIST SP 800-207 — Zero Trust Architecture
- 2020-08 (final), https://csrc.nist.gov/pubs/sp/800/207/final (DOI 10.6028/NIST.SP.800-207). A draft revision (`800-207-draft2`) exists; finalization status not confirmed this session — treat 2020 final as authoritative unless re-checked.
- **Actionable tenets for per-call gating:** no implicit trust by location/origin; authentication and authorization performed as **discrete functions before each resource access is granted** (→ pre-execution gate per tool call, not per session); resource-centric (not network-segment-centric) policy; continuous, non-implicit trust re-evaluation (→ don't cache a prior ALLOW across a session).

---

## 3. MAESTRO / Cloud Security Alliance

### 3.1 MAESTRO
- **Title:** "Agentic AI Threat Modeling Framework: MAESTRO" — CSA blog, 2025-02-06, author Ken Huang. https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro
- **7 layers + example threats:**
  1. Foundation Models — adversarial examples, model stealing, backdoors, data poisoning, DoS
  2. Data Operations — poisoning, exfiltration, infra DoS, tampering, compromised pipelines
  3. Agent Frameworks — compromised components, backdoors, input-validation attacks, supply chain
  4. Deployment & Infrastructure — container compromise, orchestration attacks, IaC manipulation, resource hijacking
  5. Evaluation & Observability — eval-metric manipulation, compromised tools, infra DoS, detection evasion
  6. Security & Compliance (cross-cutting) — security-agent poisoning/evasion/compromise, regulatory non-compliance, bias
  7. Agent Ecosystem — compromised agents, impersonation, goal manipulation, marketplace manipulation, integration risk
- Follow-on: "Applying MAESTRO to Real-World Agentic AI Threat Models — From Framework to CI/CD Pipeline," 2026-02-11.
- **Actionable:** layer tag for provenance of a given tool-call risk; our classifier operates mostly at layers 3, 4, 7.

### 3.2 Other CSA agentic-AI artifacts
- **"Agentic AI Red Teaming Guide"** — CSA, 2025-05-28, https://cloudsecurityalliance.org/artifacts/agentic-ai-red-teaming-guide. Defines **12 threat categories**: agent authorization and control hijacking; checker-out-of-the-loop; agent critical-system interaction; goal and instruction manipulation; agent hallucination exploitation; agent impact chain and blast radius; agent knowledge-base poisoning; agent memory and context manipulation; multi-agent exploitation; resource and service exhaustion; supply chain and dependency attacks; agent untraceability. Directly usable taxonomy for `suspicious_action_sequence` ("impact chain and blast radius") and general grounding.
- **"Agentic AI Identity and Access Management: A New Approach"** — CSA, 2025-08-18 (previewed 2025-03-11), https://cloudsecurityalliance.org/artifacts/agentic-ai-identity-and-access-management-a-new-approach. Recommends DIDs/Verifiable Credentials over static OAuth, JIT/ephemeral privilege grants, Zero Trust continuous authorization, audit trails cryptographically anchored to agent identity. **Actionable:** direct source for "log which agent identity took action X" requirement.
- Titles seen but not fetched in full (flag as provisional): "AI Identity Security Compliance Checklist"; "Agent Identity Governance Framework v1" (labs.cloudsecurityalliance.org).

---

## 4. MITRE ATLAS

Note: atlas.mitre.org itself could not be rendered directly this session (JS-rendered SPA, blocked WebFetch) — the technique IDs below are **[secondary-sourced]** via a documented MITRE ATLAS × Zenity Labs collaboration (announced 2025-10-21) and other mirrors, not independently re-verified against the live matrix. Treat as directionally correct, re-verify IDs before hard-coding them into shipped docs.

- AML.T0080 — AI Agent Context Poisoning (sub-techniques: .000 Memory, .001 Thread)
- AML.T0081 — Modify AI Agent Configuration
- AML.T0082 — RAG Credential Harvesting
- AML.T0083 — Credentials from AI Agent Configuration
- AML.T0084 — Discover AI Agent Configuration (.000 Embedded Knowledge, .001 Tool Definitions, .002 Activation Triggers)
- AML.T0085 — Data from AI Services (.000 RAG Databases, .001 AI Agent Tools)
- AML.T0086 — Exfiltration via AI Agent Tool Invocation
- AML.T0098 — AI Agent Tool Credential Harvesting (early-2026 addition)
- AML.T0104 — Publish Poisoned AI Agent Tool (Resource Development tactic, early-2026 addition)
- An "Escape to Host" technique reportedly added in a Feb 2026 (v5.4.0) update was **NOT FOUND at ID level** — could not retrieve its AML.T number from any accessible source this session.
- No technique explicitly named "Excessive Agency" or "multi-step attack chain" was found under that exact name — **NOT FOUND**; searches tried: `MITRE ATLAS excessive agency technique ID`.

No dedicated MITRE "AI Agent Security" publication outside ATLAS was found. The one MITRE doc surfaced ("A Sensible Regulatory Framework for AI Security," 2023-06-13) predates the agentic wave and is a general policy paper, not agent/tool-use-specific — not relevant here.

---

## 5. EU AI Act (Regulation (EU) 2024/1689)

- **Source:** https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng
- **Article 14 (Human Oversight):** high-risk AI systems must let a natural person understand capabilities/limits, detect anomalies, avoid automation bias, and — critically — **"decide not to use the system or otherwise disregard, override or reverse the output."** This is the textual basis for a REVIEW tier with a human override.
- **Article 12 (Record-keeping):** high-risk systems must **automatically** log events sufficient to identify risk-causing situations and support post-market monitoring; logs retained **≥ 6 months**; manual logging does not satisfy the requirement.
- **Article 13 (Transparency, to deployers):** providers must ship instructions covering identity, capabilities/limitations, accuracy/robustness/cybersecurity characteristics, human-oversight measures, and logging mechanisms. Applies from 2026-08-02.
- **Actionable:** our classifier's REVIEW tier is functionally an Art. 14(4)(d)-style override control; every ALLOW/REVIEW/DENY decision should feed an automatic, timestamped, non-repudiable log retained ≥ 6 months (Art. 12), documented to deployers per Art. 13.

---

## 6. Agent Identity & Authorization Standards

- **OAuth 2.1** — draft-ietf-oauth-v2-1-16, IETF OAuth WG, 2026-09-03, https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/. Obsoletes RFC 6749+6750, drops Implicit grant, mandates PKCE. Baseline role model (client / resource-server / AS) our policy engine maps tool-callers onto.
- **ID-JAG (Identity Assertion Authorization Grant / "Cross-App Access")** — draft-ietf-oauth-identity-assertion-authz-grant-04, IETF OAuth WG, 2026-05-21, https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/. Defines a JWT with `iss, sub, sub_id, aud, client_id, jti, exp, iat, resource, scope, authorization_details, act, tenant, auth_time, acr, amr`. **Actionable:** `act` (actor/delegation claim), `authorization_details` (Rich Authorization Request scoping), and `resource`/`aud` (audience binding) are exactly the fields a pre-execution classifier should inspect to confirm a tool call's authorization was scoped/issued for that specific downstream tool — direct grounding for `unauthorized_scope` and `privilege_escalation`.
- **draft-oauth-ai-agents-on-behalf-of-user-02** — individual submission, expired 2025-08-25 (last touched 2026-02-26), https://datatracker.ietf.org/doc/draft-oauth-ai-agents-on-behalf-of-user/. Adds `requested_actor`/`actor_token` and a user→agent→client delegation-chain model. Not WG-adopted — directional signal only.
- Also noted, individual/pre-WG: draft-song-oauth-ai-agent-collaborate-authz-00, draft-klrc-aiagent-auth-03.
- **SPIFFE for agents** — **NOT FOUND** as an official SPIFFE.io spec change; spiffe.io content is still microservices/K8s-scoped. All "SPIFFE for AI agents" material is third-party commentary, not a ratified extension.
- **MCP Authorization spec** — current revision **2026-07-28** (https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization, changelog same path). This revision added mandatory `iss` validation (RFC 9207), `application_type` for DCR, issuer-bound credentials, and deprecated Dynamic Client Registration in favor of Client ID Metadata Documents. Base framework (OAuth 2.1 roles, RFC 8707 `resource` parameter for audience binding, RFC 9728 Protected Resource Metadata, WWW-Authenticate step-up) established earlier (first at 2025-03-26/2025-06-18). **Actionable:** mandatory `resource` parameter = reject any tool call whose token audience ≠ target MCP server (a concrete `unauthorized_scope` check); `WWW-Authenticate: error="insufficient_scope"` is a ready-made step-up/REVIEW signal; "MUST NOT accept or transit any other tokens" is a direct confused-deputy check.
- **A2A (Agent2Agent) protocol** — v1.0.0, https://a2a-protocol.org/latest/specification/, now under Linux Foundation ("Agentic AI Foundation," announced 2026-08-27). Identity is transport-layer (Agent Card declares supported auth schemes: APIKey, HTTPAuth, OAuth2, OpenIDConnect, mTLS). **Actionable:** "MUST implement appropriate authorization scoping" per task, and MUST NOT leak exists-vs-authorized distinctions (anti-enumeration) — usable checks for cross-agent task access in `external_communication`/`untrusted_destination`.
- **W3C Agent Identity Registry Protocol Community Group** — charter proposed 2026-04-22, launched 2026-04-24, https://www.w3.org/community/agent-identity/. Scoped to DID method for agents + Verifiable-Credential agent credentials + cross-org trust + MCP/A2A/OAuth/SPIFFE integration profiles, but **no published spec/draft text exists yet** — organizational phase only. Watch, do not cite as normative.

---

## 7. Mapping Table — 11 Risk Dimensions → Standards

Legend: **[sec]** = secondary-sourced this session (ATLAS IDs, not re-verified live); "—" = no clean mapping found, not forced.

| # | Our dimension | OWASP LLM Top 10 2025 | OWASP Agentic (T1–T17) | OWASP Top 10 Agentic Apps 2026 (ASI) | MITRE ATLAS | NIST AI 100-2 category | Notes |
|---|---|---|---|---|---|---|---|
| 1 | prompt_injection_influence | LLM01 Prompt Injection | T6 Intent Breaking & Goal Manipulation; T7 Misaligned & Deceptive Behaviors; T12 Agent Communication Poisoning; T1 Memory Poisoning | ASI01 Agent Goal Hijack; ASI06 Memory & Context Poisoning | AML.T0080 AI Agent Context Poisoning **[sec]** | GenAI Misuse/Abuse (indirect prompt injection named explicitly, 2025 ed.) | Strongest, cleanest cross-framework mapping of all 11 |
| 2 | unauthorized_scope | LLM06 Excessive Agency | T2 Tool Misuse; T3 Privilege Compromise | ASI02 Tool Misuse and Exploitation; ASI03 Identity and Privilege Abuse | — (no technique named "Excessive Agency"; NOT FOUND) | — (access-control gap, not a ML-attack category) | See OAuth ID-JAG `resource`/`aud`/`scope` claims (§6) for the concrete check |
| 3 | sensitive_data_exposure | LLM02 Sensitive Information Disclosure; LLM07 System Prompt Leakage | T2 Tool Misuse (exfiltration via tool call) | ASI02 Tool Misuse and Exploitation | AML.T0085 Data from AI Services; AML.T0086 Exfiltration via AI Agent Tool Invocation **[sec]** | Privacy (both PredAI and GenAI classes) | Clean match on ATLAS + NIST Privacy |
| 4 | untrusted_destination | LLM02 Sensitive Information Disclosure (partial) | T12 Agent Communication Poisoning; T16 Insecure Inter-Agent Protocol Abuse | ASI07 Insecure Inter-Agent Communication | AML.T0086 Exfiltration via AI Agent Tool Invocation **[sec]** | Privacy (partial) | Also see A2A Agent Card auth-scheme declaration + anti-enumeration rule (§6) |
| 5 | privilege_escalation | LLM06 Excessive Agency | T3 Privilege Compromise | ASI03 Identity and Privilege Abuse | AML.T0098 AI Agent Tool Credential Harvesting; AML.T0083 Credentials from AI Agent Configuration; AML.T0082 RAG Credential Harvesting **[sec]** | — (access-control gap, not in the ML-attack taxonomy) | CSA "Agentic AI IAM" artifact (§3.2) is the deepest primary source |
| 6 | destructive_or_irreversible_action | LLM06 Excessive Agency (autonomy/permissions facet) | T11 Unexpected RCE and Code Attacks | ASI05 Unexpected Code Execution (RCE) | — (no exact match found) | — | EU AI Act Art. 14 override control is the direct regulatory hook, not a threat-taxonomy one |
| 7 | financial_commitment | LLM10 Unbounded Consumption (cost/resource facet only — imperfect) | T4 Resource Overload (imperfect — DoS/cost framing, not contractual-commitment framing) | — | — | — | **No framework defines "financial commitment/purchase" as a discrete category** — say so plainly; this dimension is not covered by any standard surveyed |
| 8 | external_communication | LLM02 Sensitive Information Disclosure (partial) | T12 Agent Communication Poisoning; T16 Insecure Inter-Agent Protocol Abuse | ASI07 Insecure Inter-Agent Communication | AML.T0086 Exfiltration via AI Agent Tool Invocation **[sec]** | Privacy (partial) | Overlaps with #4; A2A/MCP authorization fields (§6) are the actionable control surface |
| 9 | policy_conflict | — | T7 Misaligned & Deceptive Behaviors (loose — deception framing, not policy-conflict framing) | — | — | — | Not a threat-taxonomy concept in any surveyed doc — it's a governance/GOVERN-function concept (NIST AI RMF), not a threat ID; do not force a threat mapping |
| 10 | suspicious_action_sequence | — | T5 Cascading Hallucination Attacks; T13 Rogue Agents in Multi-Agent Systems | ASI08 Cascading Failures; ASI10 Rogue Agents | — (no single sequence-detection technique found) | — | CSA Red Teaming Guide's "Agent Impact Chain and Blast Radius" (§3.2) is the closest primary-source category, but it's CSA not MITRE/OWASP-Top10/NIST |
| 11 | insufficient_context | LLM09 Misinformation (loose) | T5 Cascading Hallucination Attacks | — | — | — (not an adversarial-attack category — it's a model-capability risk) | Clean match to **NIST AI 600-1 "Confabulation"** risk (not AI 100-2 — different NIST doc, see §2.2) |

**Honest gaps to flag in our threat model doc:** dimensions 6, 7, 9, and 10 have no clean ATLAS or NIST AI 100-2 mapping, and dimension 7 (`financial_commitment`) has essentially no mapping in *any* surveyed framework — none of OWASP/NIST/MITRE/CSA treat "agent commits money/enters a contract" as a first-class category. Dimension 9 (`policy_conflict`) is likewise absent from every threat taxonomy surveyed; it belongs conceptually to NIST AI RMF's GOVERN function rather than to any attack/threat list. These should be documented as genuinely novel dimensions in our risk model, not retrofitted onto an ill-fitting ID.

---

## 8. Explicit NOT-FOUND / unverified summary

- OWASP "Agentic AI Top 10" (exact name) — NOT FOUND; superseded/renamed as "OWASP Top 10 For Agentic Applications 2026" (§1.4).
- NIST AI 100-2e2025 fine-grained sub-technique IDs — not extracted; only top-level categories verified.
- NIST AI 600-1 per-risk ~400 suggested actions — not independently re-extracted from PDF body; risk-name list corroborated via secondary NIST-derived sources.
- NIST COSAIS agent-specific control overlays — scoped as future use cases, **no content published** as of 2026-09-20.
- SPIFFE for AI agents — NOT FOUND as an official spec; third-party commentary only.
- W3C Agent Identity Registry Protocol CG — exists (charter, org phase) but has **no published normative text**.
- MITRE ATLAS live matrix — could not be fetched directly this session; all new agentic technique IDs (AML.T0080–T0086, T0098, T0104) are **[secondary-sourced]** and should be re-verified against atlas.mitre.org before being hard-cited elsewhere. An "Escape to Host" technique's ID was NOT FOUND.
- MITRE standalone "AI Agent Security" publication (outside ATLAS) — NOT FOUND.
