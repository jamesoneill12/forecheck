# Commercial & Infrastructure Landscape Scan — Pre-Execution Agent Risk Scoring

Date of research: 2026-09-20. Scope: agent firewalls / MCP gateways / runtime authorization / agent-identity products. Crux question asked of every entry: **does this ship a pre-execution, per-action, multi-dimensional, calibrated numeric risk SCORE (not just a policy verdict)?**

Method: WebSearch + WebFetch against official docs, official product pages, official GitHub repos, and official press releases only. Every acquisition claim below is checked against a primary source with a date. Anything not confirmed from a primary source is marked **UNVERIFIED**. Vendor marketing claims that cannot be independently verified are labeled "vendor claim."

---

## 1. Agent Firewalls / Runtime Guardrails

Six acquisitions in this category were verified against primary sources (press releases / official blogs):

| Acquirer | Target | Status/date | Primary source |
|---|---|---|---|
| Snyk | Invariant Labs | Announced 2025-06-24 | [snyk.io/news](https://snyk.io/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation/) |
| Check Point | Lakera | Announced 2025-09-16 (~$300M, closing Q4 2025) | [checkpoint.com press release](https://www.checkpoint.com/press-releases/check-point-acquires-lakera-to-deliver-end-to-end-ai-security-for-enterprises/) |
| SentinelOne | Prompt Security | Signed 2025-08-05, closed 2025-09-05 (~$180M) | [sentinelone.com press release](https://www.sentinelone.com/press/sentinelone-to-acquire-prompt-security-to-advance-genai-security/) |
| Cato Networks | Aim Security | Announced 2025-09-03 | [catonetworks.com press release](https://www.catonetworks.com/news/cato-acquires-aim-security-to-extend-sase-leadership-and-secure-enterprise-ai-transformation/) |
| F5 | CalypsoAI | Announced ~2025-09-17, closed 2025-09-26 (~$145-180M) | [f5.com press release](https://www.f5.com/company/news/press-releases/f5-to-acquire-calypsoai-to-bring-advanced-ai-guardrails-to-large-enterprises) |
| Cisco | Robust Intelligence | Intent announced 2024-08-26 | [Cisco Blogs](https://blogs.cisco.com/news/fortifying-the-future-of-security-for-ai-cisco-announces-intent-to-acquire-robust-intelligence) |

(Unprompted but relevant: Cisco also acquired **Astrix Security**, intent announced 2026-05-04, ~$400M — [Cisco Blogs](https://blogs.cisco.com/news/cisco-announces-intent-to-acquire-astrix-security), confirmed on [Astrix's own blog](https://astrix.security/learn/blog/a-new-chapter-astrix-security-is-joining-cisco/); see §3.10.)

Crux finding stated up front: of all 15 products below, **none document a numeric, per-dimension, calibrated probability for a single pre-execution tool call.** The landscape splits into: (a) ordinal/categorical confidence buckets (Lakera L1–L5, Azure severity 0/2/4/6, Model Armor LOW/MEDIUM/HIGH-and-above), explicitly *not* documented as calibrated probabilities; (b) single aggregate 0–100 or 0–1 scores that are posture/exposure-level (Zenity AIEM, CalypsoAI CASI, HiddenLayer asset risk) or MCP-server/agent-level (Prompt Security), not per-call/per-dimension; (c) pure boolean/policy verdicts (Invariant Guardrails `raise`, Azure Prompt Shields `attackDetected`, Palo Alto `category: malicious|benign`, Cisco `is_safe`); (d) deterministic formal-logic verification (AWS Automated Reasoning: VALID/INVALID/MIXED, not probabilistic at all).

### 1.1 Invariant Labs (now part of Snyk) — Guardrails DSL, mcp-scan, Explorer
- Open source (Apache-2.0), [github.com/invariantlabs-ai/invariant](https://github.com/invariantlabs-ai/invariant). Inspects single tool calls and full agent traces — rules operate over `Message`/`ToolCall` objects; mcp-scan intercepts individual MCP tool calls.
- **Explicitly rule-based**: *"Invariant Guardrails is a comprehensive rule-based guardrailing layer for LLM or MCP-powered AI applications."* Rules fire via `raise 'message' if: <condition>` (e.g. `raise 'Untrusted email recipient' if: call is tool:send_email`), returning `AnalysisResult(errors=[...])` — a violation list, not a numeric score. No numeric field exists anywhere in the DSL or docs.
- Identity/permissions/org-policy: partial — rules can reference tool/args/sender, no first-class identity/permission schema; the DSL itself *is* the org-policy layer.
- Self-hostable (OSS); deployed via Gateway which evaluates rules pre/post each LLM and MCP request. Pricing: free/OSS core, Explorer SaaS tier exists.
- **Gap vs. us**: closest architectural analog to our downstream deterministic policy engine (a rules DSL over structured tool-call/trajectory data) — but zero probabilistic/ML classification layer.

### 1.2 Lakera Guard (now part of Check Point, pending close)
- Closed SaaS, [docs.lakera.ai](https://docs.lakera.ai/docs/defenses). Inspects prompt/content via the Guard API; "Agent Behavior Defense" adds tool allow/deny controls.
- **Ordinal confidence levels, explicitly not continuous probabilities**: *"AI Guardrails' detectors provide a confidence level indicating the probability that the analyzed content contains the specific threat type"* — but the levels are discrete: *"L1 Confident, L2 Very likely, L3 Likely, L4 Less likely, L5 Unlikely"* ([docs.lakera.ai/docs/api/results](https://docs.lakera.ai/docs/api/results)), explicitly analogized to *"OWASP's paranoia level definitions for WAFs"* — borrowed ordinal convention, not a validated/calibrated probability. The API's primary output is binary (`"flagged": true/false`); per-detector confidence only surfaces via an optional `breakdown` parameter.
- **Latency claim (vendor)**: "sub-50ms runtime latency."
- **Gap vs. us**: multi-category detector taxonomy is close to "per-dimension," but categories are ordinal buckets with no numeric-to-percentage mapping documented, and scope is single-turn content, not full pre-execution tool-call context (args/identity/target).

### 1.3 Zenity
- Closed SaaS, [zenity.io/platform](https://zenity.io/platform/ai-exposure-management). Two products: **AI Exposure Management** (build-time attack-path discovery + runtime confirmation) and **AIDR** (runtime, full session sequence — *"reads the full sequence, not just the individual moments"*).
- AIEM: **single opaque 0–100 score, for exploitable attack paths (posture), not a single pre-execution tool call**: *"Every issue gets a risk score from 0 to 100 with a clear severity: critical, high, medium, or low. The same input always produces the same score"* — that determinism claim is not a calibration claim. AIDR (the actual pre-execution runtime layer) drops the score entirely: *"Findings that fire in real time carry an action of Detected or Prevented"* — binary, no score.
- **Gap vs. us**: the 0–100 score is offline/build-time exposure-graph scoring; live runtime enforcement is a binary action with no score at all.

### 1.4 Noma Security
- Closed SaaS, [noma.security/platform/runtime-protection](https://noma.security/platform/runtime-protection/) (also AWS Marketplace). **Closest input-schema match found in the entire survey**: *"Noma monitors the full behavioral chain of every agent session (prompts, tool calls, data access, actions)"* and *"combines it with posture context like identity, data, and blast radius"* — i.e., identity + trajectory + resource/data context, matching several of our named input fields directly.
- **Output is categorical, not scored**: every detector resolves to *"monitor, alert, block, or mask"* — no score/percentage/confidence language found anywhere in primary Noma materials, despite hybrid ML detectors (*"proprietary AI models trained specifically for security analysis"*).
- Self-hostable: contested — Noma claims on-prem+SaaS options; third-party technical review says the policy-decision plane stays Noma-hosted.
- **Gap vs. us**: closest input-context match of any vendor surveyed, but output is a categorical action, not a calibrated per-dimension probability.

### 1.5 Prompt Security (now part of SentinelOne)
- Closed SaaS, [sentinelone.com/platform/securing-ai-prompt](https://www.sentinelone.com/platform/securing-ai-prompt/). Inspects tool/MCP calls in real time: *"inspect tool calls and agent interactions in real time, stopping attacks at the moment of execution."*
- **Strongest "risk score" language found among agent-firewall vendors, but scoped to MCP servers, not calls**: *"Risk-Based Enforcement: assess and score each server's threat profile before agents act"; "continuous review of agent permissions using dynamic risk scoring"* ([sentinelone.com/blog/prompt-security-for-agentic-ai](https://www.sentinelone.com/blog/prompt-security-for-agentic-ai/)). No numeric scale or per-dimension breakdown documented; no calibration methodology published.
- **Gap vs. us**: aggregate, object-scoped (server/agent reputation) score mapped to graduated actions (allow/block/filter/redact) — not a per-call, per-dimension, context-conditioned probability for an individual tool invocation.

### 1.6 Aim Security (now part of Cato Networks)
- Closed SaaS/on-prem hybrid, ~$100k/yr list price on AWS Marketplace. Inspects *"prompts, LLM and chatbot responses, and agentic AI interactions"* (official solution brief). ML-based detection (*"proprietary models trained to detect all types of runtime AI attacks and compliance violations"*) plus regex/semantic rules.
- **Purely binary/policy verdict — no score of any kind found**: enforcement model is *"block, monitor and anonymize based on data classification and inferred intent."* Zero mentions of "risk score," "%," or "confidence" in the official brief — the clearest binary-verdict case in the whole survey.

### 1.7 Witness AI
- Closed SaaS, [witness.ai](https://witness.ai/). MCP Catalog scores *tools* pre-approval against known taxonomies: *"WitnessAI's MCP Catalog scores known tools against OWASP and CVE risk classes"* — a static catalog rating, not a live per-call probability. Runtime layer (AIDR/Agentic Control) is session-aware (*"reads the full sequence, not just the individual moments"*) and ML-based on "behavioral intent," but resolves to audit/block: *"every blocked tool call generates an audit record with user, agent, tool, and rule."*
- **Gap vs. us**: no evidence of a numeric, per-dimension, pre-execution score for an individual tool call; runtime enforcement is audit/block-oriented despite ML-based intent detection.

### 1.8 CalypsoAI (now part of F5)
- Closed SaaS. Red-Team (pre-deployment adversarial testing) / Defend (real-time inference-layer protection) / Observe (monitoring). **CASI is a model-level composite security score from red-teaming benchmarks — offline, not pre-execution, not per-tool-call**: *"CASI is a metric... A higher CASI score indicates a more secure model or application,"* with a component "Agentic Resistance Score (ARS)." The live Defend module is described only as detect/block in real time, with no documented per-interaction numeric field.
- **Gap vs. us**: CASI/ARS demonstrate market appetite for composite scoring, but it's a red-team benchmark artifact, not a live per-tool-call classifier output.

### 1.9 Straiker
- Closed SaaS (founded 2025, $64M Series A June 2026). Discover AI (posture) / Ascend AI (pre-deployment adversarial testing, per-application risk scores) / Defend AI (runtime — *"inspects every prompt, reasoning step, and tool call"*).
- Runtime is an **aggregate detection-rate claim, not a per-call score**: *"Defend AI enforces runtime guardrails on every tool call, blocking unauthorized actions and data exfiltration at 98%+ accuracy... in under 300ms."* "98%+ accuracy" is a top-line classifier-accuracy marketing claim (no reliability diagram, no Brier score, no per-bucket empirical validation) — not calibration. Ascend AI's "per-application risk scores" are pre-deployment testing artifacts, not runtime per-call output.
- **Published latency claim**: <300ms blocking latency (straiker.ai) — one of the only vendors surveyed with a concrete number.
- **Gap vs. us**: real-time per-tool-call inspection with a published latency SLA, but no numeric per-call score exposed and "98%+ accuracy" is an unverified aggregate claim, not calibration.

### 1.10 HiddenLayer
- [hiddenlayer.com](https://hiddenlayer.com/), [docs.hiddenlayer.ai](https://docs.hiddenlayer.ai/). AIDR inspects model inference/agent interactions; agentic runtime capabilities (~March 2026) monitor multi-step tool calls (*"reconstructing every session to see how agents interact with data, tools, and other agents"* — trajectory-aware).
- Model/asset-level risk scoring exists but is posture-level: *"HiddenLayer scores deployed AI models by risk level based on data sensitivity processed, deployment scope, capability classification, and applicable regulatory requirements"* — computed once per asset, not per tool call. The **Interactions API schema returns an `analysis` array of detector objects each with a `detected` boolean field, not a numeric score** — confirmed from the API reference.
- **Gap vs. us**: per-detector findings array is structurally close to "per-dimension," but each dimension is a boolean (`detected: true/false`), not a probability.

### 1.11 Cisco AI Defense (successor to Robust Intelligence, and now also absorbing Astrix Security)
- [developer.cisco.com/docs/ai-defense-inspection](https://developer.cisco.com/docs/ai-defense-inspection/inspect-conversations/). Inspects single prompt/completion via the Inspection API; also MCP servers/tools (skill scanner) and supply-chain assets.
- **Confirmed API schema — ordinal severity + boolean, not calibrated probability**: `"is_safe"` (boolean), `"severity"` ∈ {NONE_SEVERITY, LOW, MEDIUM, HIGH}, `"classifications"` ∈ {SECURITY_VIOLATION, PRIVACY_VIOLATION, SAFETY_VIOLATION, RELEVANCE_VIOLATION}. This *is* multi-category (4 classification labels — the closest thing to "multi-dimensional" among closed-source runtime products), but each is a presence/absence label, and severity is one ordinal field for the whole response with no documented probability mapping.
- **Gap vs. us**: 4-category classification is genuinely multi-dimensional in structure, but categorical, not probabilistic, and zero calibration documentation.

### 1.12 Palo Alto Networks Prisma AIRS / AI Runtime Security
- [docs.paloaltonetworks.com/ai-runtime-security](https://docs.paloaltonetworks.com/ai-runtime-security), [pan.dev/airs](https://pan.dev/airs/). GA (Prisma AIRS 3.0, March 2026). Inspects single prompt/model response via API Intercept; also network-layer traffic.
- **Confirmed runtime scan API is a literal boolean** — example JSON: `"action": "block", "category": "malicious"` — *"If there is a prompt or response detected, the category in the response will be set to malicious. If not the category will be benign."* No numeric field at all — the least granular schema of any product surveyed. (Separately, an offline "AI Red Teaming" product produces a benchmark-style "risk score" combined with attack-success-rate metrics — pre-deployment, not runtime per-call.)
- **Gap vs. us**: binary `malicious`/`benign` runtime classification, zero granularity.

### 1.13 Microsoft — Defender for AI / Azure AI Content Safety Prompt Shields + Entra Agent ID
Four sub-products, each answering the crux question differently, all confirmed via `learn.microsoft.com`:
- **(a) Prompt Shields** — GA, closed. **Purely boolean, confirmed via live API example**: `{"userPromptAnalysis": {"attackDetected": true}}`, field explicitly typed **Boolean**. No numeric score.
- **(b) Azure AI Content Safety harm categories** — GA. Categories: Hate/Fairness, Sexual, Violence, Self-Harm, plus a **Task Adherence** category specifically for agents (*"identifies discrepancies, such as misaligned tool invocations, improper tool input or output relative to user intent"*) — 5 categories is the closest thing to genuine "per-dimension" found in the whole survey. But severity is a documented **discrete 0–7 scale, typically trimmed to 0/2/4/6**, with no stated probability meaning for any severity value.
- **(c) Entra Agent ID / ID Protection "Risky Agents"** — GA (Agent 365). **Explicitly offline, not pre-execution**: *"At this time, all risk detections for risky agents are offline."* Output is a categorical risk level (None/Low/Medium/High) from 8 named anomalous-activity detectors, attributed to the agent identity/session, not to a specific tool call.
- **(d) Defender for Cloud AI threat protection** — GA; produces XDR alerts (built atop boolean Prompt Shields + threat intel), not a scored classifier output.
- **Gap vs. us**: Content Safety's 5-category taxonomy (including an agent-specific Task Adherence dimension) is a genuine multi-dimensional precedent worth citing directly, but every score in the Microsoft stack is boolean, ordinal-uncalibrated, or offline/identity-level categorical — never a per-call numeric probability.

### 1.14 AWS Bedrock Guardrails + Automated Reasoning checks
- [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-content-filters.html). Content filters explicitly **do not inspect tool calls at all**: *"In tool use (function calling) workloads, they do not evaluate tool results (toolResult), tool definitions (toolSpec), or model-generated tool call arguments (toolUse.input)"* — a documented, explicit blind spot for our exact use case. Filter strength is an enum (`NONE|LOW|MEDIUM|HIGH`) per category (Hate/Insults/Sexual/Violence/Misconduct), confirmed via the `CreateGuardrail` API schema (`inputStrength`/`outputStrength` fields) — not a float.
- **The one genuinely continuous, documented, per-dimension score found in this entire survey**: **Contextual grounding checks** produce two independent continuous scores 0–0.99 — *"Contextual grounding checks generate confidence scores corresponding to grounding and relevance for each model response... You can configure threshold values of grounding and relevance between 0 and 0.99"* ([docs.aws.amazon.com/bedrock/.../guardrails-contextual-grounding-check.html](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html)). Important limitation: this scores **output text vs. a reference source (hallucination detection)**, not a pre-execution tool-call risk classification, and there is no calibration methodology stated — it is a threshold knob, not a validated probability (no "0.7 = 70% empirical rate" claim anywhere).
- **Automated Reasoning checks** are fully deterministic SMT-style formal-logic verification, explicitly the opposite of probabilistic: outputs are **Valid / Invalid / Mixed**, with counter-example variable assignments on Invalid — *"mathematically sound, logic-based algorithmic verification,"* not a risk score.
- **Gap vs. us**: (1) explicitly excludes tool-call arguments from content filtering entirely; (2) the one continuous score that exists (grounding/relevance) targets output-hallucination-vs-source, not action-risk, and is uncalibrated; (3) Automated Reasoning deliberately avoids probability in favor of deterministic proof — a different paradigm from ours. Still, this continuous 0–0.99 per-dimension (grounding, relevance) precedent is the closest thing to our design found anywhere in the survey and is worth citing directly in project rationale.

### 1.15 Google Model Armor
- [docs.cloud.google.com/security-command-center/docs/model-armor-overview](https://docs.cloud.google.com/security-command-center/docs/model-armor-overview). Inspects prompt/response text (`sanitizeUserPrompt`/`sanitizeModelResponse`); no documented tool-call-specific inspection.
- **Ordinal confidence-level buckets, explicitly defined as likelihood tiers, not continuous probabilities**: *"'High': Identifies content with a high likelihood of violation"; "'Medium and above': ...medium or high likelihood"; "'Low and above': ...low, medium, or high likelihood."* Enforcement resolves to block/allow: *"When Model Armor detects a policy violation... it logs the event and provides a verdict to block the request."* Separately, Security Command Center's AI angle surfaces "attack exposure scores" across an AI inventory — fleet/posture-level prioritization, not live per-call scoring.
- **Gap vs. us**: multiple detection categories (jailbreak, sensitive data, malicious URLs, prompt injection) per template is structurally close to multi-dimensional, but confidence is a 3-tier ordinal label per category with no continuous score, no tool-call-specific inspection, and no calibration evidence.

**Category summary**: across all 15 products, **zero** were found with primary-source documentation of a calibrated, multi-dimensional, per-action, pre-execution numeric risk probability for a single tool call. Ordinal severity/confidence buckets (Lakera L1–L5, Azure 0/2/4/6, AWS NONE/LOW/MEDIUM/HIGH, Model Armor LOW/MEDIUM/HIGH-and-above, Cisco NONE_SEVERITY/LOW/MEDIUM/HIGH) are the dominant "score-like" pattern, uniformly borrowed from WAF/IDS conventions and never framed as calibrated probabilities. Where a genuine 0–100/0–1 "risk score" is marketed (Zenity AIEM, Prompt Security, CalypsoAI CASI, Straiker, HiddenLayer), it is consistently scoped **above** the single tool call — attack path, MCP server, model, application, or asset — and is single-dimension, not per-risk-dimension. **AWS Bedrock's contextual grounding check (continuous 0–0.99 grounding/relevance scores) is the single closest precedent to "calibrated per-dimension probability" found anywhere in the competitive set**, but it scores output-vs-source hallucination, not action risk, and has no calibration validation documented. Trajectory/sequence awareness is claimed by several newer agent-security startups (Zenity AIDR, Noma, Witness AI, HiddenLayer agentic runtime, Invariant Labs) but the hyperscaler products (Azure/AWS/GCP/Palo Alto) are uniformly single-request/stateless.

---

## 2. MCP Gateways / Proxies

### 2.1 Docker MCP Gateway / MCP Catalog & Toolkit
- **Org**: Docker, Inc.
- **Status**: GA. Open source core (gateway CLI/runtime); Enterprise tier adds identity-provider integration. Docs: [docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/); announcement: [docker.com/blog/docker-mcp-gateway-secure-infrastructure-for-agentic-ai](https://www.docker.com/blog/docker-mcp-gateway-secure-infrastructure-for-agentic-ai/).
- **Inspects**: single tool call at the proxy layer (signature checks, secret/network controls, pre/post interceptors that can "block or transform risky actions before they reach your systems" — [docker.com/blog/mcp-security-explained](https://www.docker.com/blog/mcp-security-explained/)). No trajectory memory documented.
- **Identity + permissions + org policy input**: partial — container isolation + secret/network allowlists; full IdP-based policy requires the Enterprise tier (not confirmed as multi-dimensional risk policy, just access control).
- **Model**: rules/interceptors, not ML classification, per the official blog.
- **Numeric calibrated risk score?** No — official docs describe binary intercept/block/transform actions and pass/fail security-scan checks on MCP servers, not a per-call calibrated probability. UNVERIFIED beyond that: no documentation found of any risk-score field on individual tool calls.
- **Calibration evidence**: none found.
- **Trajectory awareness**: not documented.
- **Latency/hardware**: not published.
- **Self-hostable**: yes (core gateway is open source; runs via Docker Desktop/CLI).
- **Pricing**: gateway itself free; Enterprise identity features gated behind Docker Business/Enterprise plans (specific price not published).
- **Overlap**: intercepts individual tool calls pre-execution, similar surface area to our classifier's input point.
- **Gap**: no learned risk model at all — it is a rules/allowlist proxy, not a probability-producing classifier.

### 2.2 MCP Defender
- **Org**: independent open-source project ([github.com/MCP-Defender/MCP-Defender](https://github.com/MCP-Defender/MCP-Defender)).
- **Status**: OSS desktop app, actively maintained (150 stars / 12 forks at time of check). License per repo (MIT-style, verify in repo before citing precisely).
- **Inspects**: MCP traffic (tool calls/responses) between desktop AI apps (Cursor, Claude Desktop, VS Code, Windsurf) and MCP servers — "automatically scans and blocks malicious MCP traffic."
- **Identity+permissions+org policy**: no — desktop-local scanning tool, no enterprise policy/identity plane documented.
- **Model**: signature/pattern-based scanning per repo description ("scans and blocks malicious...traffic"); no ML risk-scoring documented.
- **Numeric calibrated risk score?** No — binary scan/block verdict only, per repo README.
- **Calibration evidence**: none.
- **Trajectory awareness**: not documented (per-call scanning).
- **Latency/hardware**: not published.
- **Self-hostable**: yes, it's a local desktop app by design.
- **Pricing**: free/open source.
- **Overlap**: pre-execution single-tool-call inspection point.
- **Gap**: no identity/org-policy context, no multi-dimensional score, desktop-scoped not enterprise-scoped.

### 2.3 Obot MCP Gateway
- **Org**: Obot AI ([obot.ai](https://obot.ai/), [github.com/obot-platform/obot](https://github.com/obot-platform/obot)).
- **Status**: GA / open source platform with hosted option. Docs: [docs.obot.ai/concepts/mcp-gateway](https://docs.obot.ai/concepts/mcp-gateway/); launch press release: [prnewswire.com/.../obot-ai-launches-mcp-gateway](https://www.prnewswire.com/news-releases/obot-ai-launches-mcp-gateway-to-help-enterprises-manage-secure-and-scale-ai-integration-302527022.html).
- **Inspects**: connection-level auth (validates users against IdP), server deployment, and per-call proxying; a "MCP Server Shim" alongside each server does authorization, audit logging, webhook filters, token exchange.
- **Identity+permissions+org policy**: yes for identity/authZ (OAuth + access policies) — but this is deterministic authorization/audit, not a risk-probability model.
- **Model**: rules/policy engine + audit logging, not ML.
- **Numeric calibrated risk score?** No — docs describe authentication, authorization, and audit as the three functions; no risk-score field documented.
- **Calibration evidence**: none.
- **Trajectory awareness**: audit logging exists (historical record) but no documented sequence-aware scoring.
- **Latency/hardware**: not published.
- **Self-hostable**: yes, explicitly open source, deployable via Docker/Kubernetes.
- **Pricing**: open-core; hosted/enterprise pricing not fully public.
- **Overlap**: sits at the same pre-execution interception point (every tool call passes through the gateway + shim).
- **Gap**: pure auth/audit — no risk scoring dimension at all.

### 2.4 Solo.io agentgateway
- **Org**: Solo.io ([agentgateway.dev](https://agentgateway.dev/), [docs.solo.io/agentgateway](https://docs.solo.io/agentgateway/2.3.x/mcp/auth/setup/)).
- **Status**: open source proxy (Apache-licensed per project norms — verify exact license in repo) with a Solo Enterprise commercial tier.
- **Inspects**: MCP/A2A traffic — tool federation, OAuth auth setup, "control access to tools" (allow/deny per tool), virtual MCP composition.
- **Identity+permissions+org policy**: yes for OAuth-based identity and per-tool access lists; described as governance, not risk scoring.
- **Model**: rules/policy (tool allow-lists, auth policies).
- **Numeric calibrated risk score?** No — "drop-in security, observability, and governance," access control described as allow/deny per tool, no probability output found.
- **Calibration evidence**: none.
- **Trajectory awareness**: not documented.
- **Latency/hardware**: not published (Envoy-based data plane, general proxy latency characteristics not risk-specific).
- **Self-hostable**: yes (OSS + Kubernetes-native deployment docs).
- **Pricing**: OSS free; Enterprise tier pricing not public.
- **Overlap**: same interception point, tool-level access control.
- **Gap**: authorization/routing only, no risk model.

### 2.5 Kong AI Gateway
- **Org**: Kong Inc. ([developer.konghq.com/ai-gateway](https://developer.konghq.com/ai-gateway/)).
- **Status**: GA, closed-source core product with plugin architecture (Kong Gateway itself has an OSS edition, AI Gateway plugins are part of Kong's commercial/enterprise plugin hub — verify per-plugin licensing before quoting).
- **Inspects**: prompts/responses via plugins — AI Prompt Guard (allow/deny lists), AI Semantic Prompt Guard (semantic intent blocking), AI Custom Guardrail (delegates to external HTTP guardrail service), integrations with AWS Bedrock Guardrails and Azure AI Content Safety.
- **Identity+permissions+org policy**: Kong's broader API-gateway layer has auth/rate-limiting; not documented as feeding a unified risk model.
- **Model**: rules (keyword/allow-deny lists) + semantic matching; delegates deeper ML scoring to third-party guardrail services (Bedrock/Azure) rather than shipping its own calibrated model.
- **Numeric calibrated risk score?** No — plugin docs describe block/flag/allow actions per policy, not a calibrated per-dimension probability native to Kong.
- **Calibration evidence**: none; whatever scoring exists is inherited from the third-party guardrail service being called (e.g., Bedrock Guardrails), not from Kong itself.
- **Trajectory awareness**: not documented — per-request plugin evaluation.
- **Latency/hardware**: Kong publishes general gateway latency benchmarks (not guardrail-specific); not cited here to avoid overreach.
- **Self-hostable**: Kong Gateway OSS is self-hostable; AI Gateway plugin tier availability depends on license.
- **Pricing**: Kong Konnect/Enterprise pricing not fully public; contact-sales model typical.
- **Overlap**: pre-execution prompt/response inspection point, orchestrates third-party guardrail calls.
- **Gap**: no native calibrated risk classifier; it's an orchestration layer over other vendors' binary/flag guardrails.

### 2.6 IBM ContextForge (MCP Context Forge)
- **Org**: IBM ([github.com/IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge), [ibm.github.io/mcp-context-forge](https://ibm.github.io/mcp-context-forge/)).
- **Status**: open source (Apache-2.0 per repo — verify), pip-installable (`mcp-contextforge-gateway`).
- **Inspects**: federates MCP/A2A/REST/gRPC behind a unified endpoint; "40+ plugins" for guardrails, observability (OpenTelemetry).
- **Identity+permissions+org policy**: OAuth 2.0 integration documented; rate limiting/auth/retries at the API-gateway layer.
- **Model**: rules/plugin-based; no ML risk model documented in the overview/architecture docs.
- **Numeric calibrated risk score?** No — "centralized discovery, guardrails and management" described at the policy/routing level, no calibrated score field found.
- **Calibration evidence**: none.
- **Trajectory awareness**: not documented.
- **Latency/hardware**: not published.
- **Self-hostable**: yes, this is the primary deployment model.
- **Pricing**: free/open source (IBM-sponsored community project).
- **Overlap**: pre-execution interception across MCP/A2A/REST tool calls.
- **Gap**: plugin/rules architecture, no native risk-probability output.

### 2.7 Lasso Security MCP Gateway
- **Org**: Lasso Security ([github.com/lasso-security/mcp-gateway](https://github.com/lasso-security/mcp-gateway), [lasso.security](https://www.lasso.security/resources/lasso-releases-first-open-source-security-gateway-for-mcp)).
- **Status**: open source (first OSS security-centric MCP gateway per their announcement).
- **Inspects**: proxies/orchestrates MCP servers; ships a "security scanner that analyzes MCP servers for potential risks before they're loaded," described in their own materials as "multi-dimensional security analysis"; guardrail plugins for PII masking (Presidio), secret masking, prompt-injection and harmful-content detection (proprietary "lasso" plugin).
- **Identity+permissions+org policy**: not the focus — scanning is of the MCP server/tool definitions, not caller identity or org policy.
- **Model**: hybrid — pattern/plugin-based masking plus (per marketing copy) some detection models for prompt injection/harmful content in the proprietary "lasso" plugin; exact model type not disclosed in public docs.
- **Numeric calibrated risk score?** Vendor claim of "multi-dimensional security analysis" for pre-load server scanning, but no documentation found of a numeric, calibrated, per-tool-call probability at runtime — the runtime guardrail plugins are described as detect/mask/block, not scored. Label the "multi-dimensional" phrase as **vendor claim, unverified for calibration**.
- **Calibration evidence**: none found.
- **Trajectory awareness**: not documented.
- **Latency/hardware**: not published.
- **Self-hostable**: yes (pip-installable OSS gateway).
- **Pricing**: OSS free; Lasso's broader enterprise platform pricing not public.
- **Overlap**: closest of the gateway category to "multi-dimensional analysis" language, worth flagging as adjacent.
- **Gap**: no evidence of calibration; scanning target is MCP server manifests, not live per-action context (identity, trajectory, destination trust).

### 2.8 Cloudflare AI Gateway (incl. "AI Security for Apps" / Firewall for AI)
- **Org**: Cloudflare ([developers.cloudflare.com/ai-gateway](https://developers.cloudflare.com/ai-gateway/), [developers.cloudflare.com/ai-gateway/features/guardrails](https://developers.cloudflare.com/ai-gateway/features/guardrails/)).
- **Status**: GA, closed-source SaaS (part of Cloudflare's platform).
- **Inspects**: prompts and model responses — PII detection, unsafe/custom topic detection, DLP scanning; "Guardrails" evaluates prompts against safety parameters (violence, hate, sexual content) and flags/blocks pre-model-call.
- **Identity+permissions+org policy**: no agent-identity/permission model documented; this is content-safety filtering on the LLM I/O path, not an authorization system.
- **Model**: classifier-based content-safety detection (categories), rules for DLP/PII regex-style matching.
- **Numeric calibrated risk score?** No — docs describe flag/block decisions against configured safety thresholds per category, not a calibrated multi-dimensional probability exposed to the caller.
- **Calibration evidence**: none found.
- **Trajectory awareness**: none documented — per-request prompt/response evaluation.
- **Latency/hardware**: not specifically published for Guardrails (general AI Gateway caching/routing latency is documented, but not guardrail-scoring latency).
- **Self-hostable**: no — Cloudflare SaaS only.
- **Pricing**: bundled into Cloudflare's AI Gateway product tiers (usage-based; guardrails-specific line pricing not separately published).
- **Overlap**: pre-execution-adjacent (pre-model-call) content screening.
- **Gap**: content-safety categories (violence/hate/PII), not agent-tool-call risk dimensions (privilege, resource sensitivity, destination trust, trajectory); no identity/permissions input; no calibration evidence.

### 2.9 Pomerium (MCP support)
- **Org**: Pomerium ([pomerium.com/docs/capabilities/mcp](https://www.pomerium.com/docs/capabilities/mcp)).
- **Status**: GA/experimental-to-GA MCP support layered on Pomerium's zero-trust proxy; core Pomerium is open source (Apache-2.0), enterprise features closed.
- **Inspects**: connection + identity — enforces the same authorization policies across human, LLM, and CI-agent callers; logs every tool call.
- **Identity+permissions+org policy**: yes — this is squarely an identity-aware access-proxy (service accounts, external tokens, per-tool/per-server policy) built on Pomerium's existing zero-trust policy engine.
- **Model**: deterministic policy evaluation (identity/group-based rules), not ML.
- **Numeric calibrated risk score?** No — "enforces the same authorization policies and logs every tool call," i.e., allow/deny per policy, no probability output documented.
- **Calibration evidence**: none.
- **Trajectory awareness**: audit logging exists; no documented sequence-conditioned scoring.
- **Latency/hardware**: not published for MCP path specifically.
- **Self-hostable**: yes, core Pomerium is self-hostable OSS.
- **Pricing**: OSS free; Enterprise tier pricing not public.
- **Overlap**: identity-aware pre-execution interception of tool calls — closest of the gateways to "consumes identity+permissions" on our input list.
- **Gap**: purely deterministic policy evaluation, no risk-probability layer at all.

### 2.10 The Model Context Protocol (MCP) spec's own authorization model
- **Source**: official spec, [modelcontextprotocol.io/specification/2025-11-25/basic/authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) (and prior [2025-03-26 draft](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-03-26/basic/authorization.mdx)).
- MCP defines an OAuth 2.1–based authorization framework: MCP servers act as OAuth resource servers, a separate authorization server issues tokens, PKCE is mandated, Authorization Server Metadata (RFC 8414) and Protected Resource Metadata are used for discovery, and clients MUST use RFC 8707 Resource Indicators to bind tokens to a specific resource. Authorization is explicitly **OPTIONAL** for MCP implementations overall, and STDIO transports are told to use environment-provided credentials instead of this flow.
- **What it does NOT cover**: the spec defines *authentication and coarse authorization* (can this token call this server at all) — it has **no concept of a risk score, no per-action probability, no trajectory state, and no notion of "sensitivity of the resource being touched."** It answers "is this token valid for this resource server," not "how risky is this specific tool call in this specific context." This is the standards-layer confirmation that risk scoring is an unaddressed layer above MCP's own auth model — exactly the gap our classifier and the deterministic policy engine downstream of it would sit in.

**Category summary**: every MCP gateway/proxy examined does identity/connection-level auth, tool allow/deny lists, and content-safety pattern matching. None publish a calibrated, multi-dimensional, per-action risk probability. Lasso Security's marketing language ("multi-dimensional security analysis") is the closest verbal overlap but is unverified for calibration and targets pre-load server scanning, not live per-call scoring with identity/trajectory context.

---

## 3. Authorization / Policy Engines & Agent Identity

These products answer **"is this principal ALLOWED to do X"** — deterministic policy evaluation — not **"how RISKY is this specific action in this specific context."** That is the structural, confirmed distinction from our classifier for every entry below.

### 3.1 Oso (Oso Cloud / Polar)
- [osohq.com/docs](https://www.osohq.com/docs/reference/polar/introduction) — Polar is a declarative logic language for RBAC/ReBAC/ABAC; Oso Cloud is a fully-managed authorization service that evaluates queries against stored facts and returns allow/deny-style permission results.
- Closed SaaS (Oso Cloud) with a deprecated OSS library (`osohq/oso` marked deprecated on GitHub). Pure deterministic policy evaluation, no ML, no risk score, no trajectory awareness (stateless permission queries). Self-hostable: OSS library deprecated in favor of hosted Oso Cloud — self-hosting story is degraded. Pricing: SaaS, not fully public.
- Gap vs. us: answers "can user U do action A on resource R," full stop — no probability, no context beyond declared facts/relationships.

### 3.2 OpenFGA
- [openfga.dev](https://openfga.dev/docs/fga), CNCF **Incubating** project ([tag-security.cncf.io self-assessment](https://tag-security.cncf.io/community/assessments/projects/openfga/self-assessment/)). Google-Zanzibar-inspired ReBAC engine; relationship tuples (user, relation, object) with optional conditions.
- Open source (Apache-2.0), self-hostable, free. Deterministic graph-based relationship evaluation, no ML, no numeric risk output, no trajectory state — each check is a point-in-time relationship query.
- Gap vs. us: models "who has access to what via what relationship," not "how dangerous is this specific call right now."

### 3.3 AWS Cedar + Amazon Verified Permissions
- Cedar: open source (Apache-2.0) policy language, [cedarpolicy.com](https://docs.cedarpolicy.com/), [github.com/cedar-policy](https://github.com/cedar-policy/); announced open-sourced May 2023 ([aws.amazon.com/about-aws/whats-new/2023/05/cedar-open-source-language-access-control](https://aws.amazon.com/about-aws/whats-new/2023/05/cedar-open-source-language-access-control/)). Amazon Verified Permissions is the managed evaluation service, closed SaaS, [docs.aws.amazon.com/verifiedpermissions](https://docs.aws.amazon.com/verifiedpermissions/).
- Principal-Action-Resource-Context (PARC) model; evaluates policies and returns ALLOW/DENY. Supports "automated reasoning tools" for formal policy analysis (SMT-based verification that policies satisfy certain properties) — this is verification of the *policy set*, not a runtime risk probability for an *action instance*.
- No numeric risk score, no calibration, no trajectory. Cedar itself is self-hostable (it's a library/engine); Verified Permissions (managed) is not self-hostable.
- Gap vs. us: same allow/deny structure; Cedar's automated-reasoning angle is about proving policy correctness, not scoring live actions.

### 3.4 Open Policy Agent (OPA) / Rego
- CNCF **Graduated** (accepted 2018-03-29, graduated 2021-01-29 per [CNCF project page](https://www.cncf.io/projects/open-policy-agent-opa/)). Open source (Apache-2.0), [openpolicyagent.org](https://www.openpolicyagent.org/docs), [github.com/open-policy-agent/opa](https://github.com/open-policy-agent/opa).
- General-purpose declarative policy engine; Rego policies evaluate structured input and return a decision (which can technically be any JSON value, including a number set by policy authors) — but OPA itself provides no learned/calibrated scoring; any "score" would have to be hand-authored as a rule, not learned from data or calibrated.
- Self-hostable, free, widely embedded (Kubernetes admission control, API gateways, CI/CD). No trajectory awareness natively (stateless per-input evaluation unless the caller supplies history in the input document).
- Gap vs. us: OPA is a natural **enforcement substrate for the deterministic policy engine downstream of our classifier** — not a competitor to the classifier itself. Worth noting explicitly: our architecture's second stage (score → ALLOW/REVIEW/DENY) is exactly the kind of thing OPA/Rego is built to execute.

### 3.5 Permit.io (AI access control / Permit MCP Gateway)
- [permit.io/ai-access-control](https://www.permit.io/ai-access-control), [docs.permit.io/permit-mcp-gateway](https://docs.permit.io/permit-mcp-gateway/). Closed-core SaaS with a customer-controlled/on-prem deployment option (control plane still Permit.io-hosted or fully on-prem for air-gapped).
- Combines ReBAC (via Permit.io + OPA + OPAL) with "tools classified by risk" and human-in-the-loop consent for "critical decisions." The phrase "tools classified by risk" is a **static, admin-assigned risk tier** (e.g., a config label on a tool), not a per-call learned probability — this is the closest of the auth-layer products to using the word "risk," so flag it explicitly.
- No numeric per-dimension calibrated score documented; five-stage auth process + audit + anomaly detection, but "anomaly detection" is not further specified as ML-calibrated in public docs — mark **UNVERIFIED** for any ML claim here.
- Gap vs. us: risk is a design-time tag on a tool ("this tool is high-risk") not a runtime, context-conditioned probability for a specific call.

### 3.6 Auth0 for GenAI ("Auth for GenAI")
- [auth0.com/ai/docs](https://auth0.com/ai/docs), [github.com/auth0/auth-for-genai](https://github.com/auth0/auth-for-genai). Developer Preview status per official docs.
- OAuth2/OIDC-based auth for agents, async human-in-the-loop authorization for "critical actions," fine-grained ReBAC for RAG document access. Deterministic — token issuance/validation and permission checks, not a risk score.
- Self-hostable: no (Auth0/Okta SaaS); SDK is open source but backend is the Auth0 service.
- Gap vs. us: governs *whether an agent can obtain a token/act on a resource*, not *how risky this specific already-authorized action is*.

### 3.7 WorkOS Agent Auth (AuthKit "blueprints")
- [workos.com/docs/authkit/agent-blueprints](https://workos.com/docs/authkit/agent-blueprints). GA feature of AuthKit; closed SaaS.
- Issues short-lived, scoped tokens from a "blueprint" (permission ceiling); delegated vs. autonomous modes. Purely a token-scoping/identity mechanism — no risk score.
- Gap vs. us: defines the ceiling of what an agent *could ever* do; doesn't evaluate whether a specific call *within* that ceiling is dangerous.

### 3.8 Descope Agentic Identity / Outbound Apps
- [docs.descope.com/agentic-identity-hub](https://docs.descope.com/agentic-identity-hub), [docs.descope.com/identity-federation/outbound-apps](https://docs.descope.com/identity-federation/outbound-apps). GA; closed SaaS (Descope platform).
- Token vault + OAuth federation for connecting agents to 50+ third-party tools. Identity/credential management, not risk scoring.
- Gap vs. us: solves "how does the agent authenticate to Gmail/Slack/etc." not "should this particular Gmail send happen."

### 3.9 Okta Cross-App Access (XAA)
- [developer.okta.com/docs/concepts/xaa](https://developer.okta.com/docs/concepts/xaa/), official Okta blog Sept 2025. GA-track protocol (OIN integrations rolling out through 2026); closed platform feature (protocol itself is being positioned for broader adoption but implementation is Okta's).
- Token-exchange protocol so an AI agent can act app-to-app while preserving the signing user's identity context (MCP-compatible). Pure identity/token-exchange plumbing.
- Gap vs. us: preserves *whose* identity an action runs under; says nothing about the *riskiness* of the action itself.

### 3.10 Astrix Security (non-human identity)
- [astrix.security](https://astrix.security/). **Acquired by Cisco** — Cisco announced intent to acquire Astrix on 2026-05-04 per [Cisco's official blog](https://blogs.cisco.com/news/cisco-announces-intent-to-acquire-astrix-security) (~$400M, also reported by [Calcalistech](https://www.calcalistech.com/ctechnews/article/dy5obf581)); Astrix's own blog confirms "Astrix Security is Joining Cisco" ([astrix.security/learn/blog/a-new-chapter-astrix-security-is-joining-cisco](https://astrix.security/learn/blog/a-new-chapter-astrix-security-is-joining-cisco/)). Standalone new-license sales ended 2026-06-30 per Astrix's own site.
- Discovery + posture management for NHIs/agents/MCP servers: finds excessive privilege, vulnerable config, "abnormal activity," policy violations. "Abnormal activity" detection implies some anomaly-detection modeling, but no public doc shows a calibrated per-action risk probability — this is fleet-level posture/inventory management, not pre-execution per-call scoring. Now folds into Cisco AI Defense (see firewall section).
- Gap vs. us: inventory/posture (which agents exist, what can they reach, are they misconfigured) vs. our per-call, pre-execution decision.

### 3.11 Token Security (non-human identity)
- [token.security](https://www.token.security/). Closed SaaS. Discovery, lifecycle, "intent-aware least privilege" for NHIs/agents. Same category as Astrix — inventory/posture/lifecycle governance, not live per-action risk scoring. No numeric calibrated score documented.
- Gap vs. us: governs the identity's standing permissions over time, not a specific action's instantaneous risk.

### 3.12 Britive (non-human identity / JIT access)
- [britive.com](https://www.britive.com/), [docs.britive.com](https://docs.britive.com/docs/service-identity-federation). Closed SaaS. Just-in-time, ephemeral, zero-standing-privilege access for NHIs/agents; "high-risk actions triggering step-up authentication or human-in-the-loop approval" — again, "high-risk" here reads as an admin-configured ABAC/PBAC rule tag, not a learned/calibrated probability. Mark this specific "risk" language as **vendor phrasing, not a scored model** absent further documentation.
- Gap vs. us: JIT credential lifecycle management; the "risk" trigger is a rule condition, not our kind of output.

**Category summary**: every authorization/identity product surveyed is deterministic (RBAC/ABAC/ReBAC policy evaluation or token/credential lifecycle management). Several use the *word* "risk" (Permit.io's "tools classified by risk," Britive's "high-risk actions") but in every case this is a static, admin-assigned label or rule condition — not a calibrated, learned, per-dimension probability computed from live context. OPA is the one product in this category that is directly relevant to us as an **implementation substrate for the deterministic policy engine downstream of our classifier**, not as a competing classifier.

---

## 4. Fraud-Scoring Analogy: How Stripe Radar Actually Works

Primary source: [docs.stripe.com/radar/risk-evaluation](https://docs.stripe.com/radar/risk-evaluation) (fetched 2026-09-20) and [docs.stripe.com/radar/transaction-risk-prevention](https://docs.stripe.com/radar/transaction-risk-prevention).

- **ML score**: Radar's adaptive ML model evaluates each Charge/PaymentIntent/SetupIntent in real time and (on certain plans) exposes a `risk_score` field on the `Charge.outcome` object ranging **0–99**. Stripe states plainly: "For a small subset of payments, Stripe modifies the reported risk score so we can measure the performance of our models."
- **Risk levels are bucketed, not raw**: Stripe maps the continuous score to a small categorical `risk_level`: `highest` (≥75, blocked by default), `elevated` (≥65, sent to manual review by default), `normal`, `not_assessed`, `unknown`. This is functionally identical in shape to our proposed "score → ALLOW/REVIEW/DENY" split — Radar's score is the analog of our per-dimension probabilities, and the risk-level bucketing + default actions are the analog of our separate deterministic policy engine.
- **Deterministic rules layer sits on top of/alongside the ML score**: Radar Rules are separately authored (e.g., `:risk_score: > 70`) and can request 3DS, allow, block, or send to review — rules can *reference* the score but are themselves simple deterministic conditionals, confirming the two-layer architecture (ML score-generator + deterministic rule/policy layer) is exactly Stripe's production pattern, not just our proposal.
- **Reviewable queue**: "elevated risk" payments land in a manual review queue (plan-dependent) with "risk insights" explaining *why* a score was assigned — the closest production analog to our REVIEW verdict + explainability requirement.
- **Important limitation for the analogy**: Radar's score is fundamentally **single-dimensional** — a single fraud-likelihood probability, not a vector of calibrated probabilities across distinct risk *types* the way our 11-dimension design specifies. Stripe does not decompose "risk" into orthogonal dimensions (e.g., "likelihood of stolen card" vs. "likelihood of friendly fraud" vs. "likelihood of account takeover") in any documentation found — it is one score with categorical explanatory "insights" attached, not a multi-dimensional structured output.
- **No vendor found publicly using the explicit "Stripe Radar for agent actions" framing** in the agent-security space as of 2026-09-20. Several vendors reference "fraud detection" analogies loosely in marketing copy (not independently verified per-vendor here), but none ship the Radar architecture (continuous ML score + bucketed risk level + separate deterministic rule layer + reviewable queue) applied to agent tool calls. This is a genuine, confirmed white space for the "Radar for agent actions" tagline — with the caveat that even Radar itself is single-dimensional, so our multi-dimensional angle is a step beyond the Radar analogy, not just a port of it.

---

## 5. Closest Competitors, Ranked

Ranked by how nearly each matches our spec (pre-execution, per-action, multi-dimensional, calibrated risk probability over identity+permissions+trajectory+destination-trust+org-policy context, feeding a separate deterministic policy engine).

**1. AWS Bedrock Guardrails — Contextual Grounding Checks** — closest **numeric-precedent** match found anywhere in the survey: a genuinely continuous 0–0.99 score, and *two independent scores at once* (grounding, relevance), configured as threshold knobs on official API docs. *Remaining difference*: scores output-text-vs-reference-source hallucination, not tool-call action risk; explicitly does not extend to `toolUse.input` (content filters "do not evaluate... model-generated tool call arguments"); no calibration methodology published (thresholds, not validated probabilities); closed SaaS; only 2 dimensions, not 11; no identity/trajectory/org-policy input at all.

**2. Noma Security (AI-DR)** — closest **input schema** match: explicitly evaluates "the session around it, the identity behind the agent, the data involved, and behavior over time" per action. *Remaining difference*: output is a four-way categorical action (alert/block/mask/route-to-human), not a numeric per-dimension probability; no evidence of calibration; not open source; closed SaaS with no published architecture for how "risk" is computed internally.

**3. Prompt Security / SentinelOne** — closest **vocabulary** match: the only agent-firewall vendor found using "dynamic risk score" tied directly to graduated enforcement actions (allow/block/filter/redact). *Remaining difference*: the score is assigned to MCP **servers** (an infrastructure/reputation object), not to individual in-context tool-call instances; no per-dimension decomposition; no calibration evidence; closed SaaS.

**4. Invariant Labs / Snyk (Guardrails, mcp-scan, Explorer)** — closest **trajectory-awareness and interception-point** match: inspects full agent trajectories and intercepts every LLM/MCP request pre- and post-call, open source (Apache-2.0). *Remaining difference*: explicitly a rules DSL ("simple Python-inspired matching rules") returning pass/fail — no learned model, no score of any kind, let alone a calibrated one; no first-class identity/permissions/org-policy input schema.

**5. Stripe Radar (out of category, architectural reference)** — closest **architectural pattern** match: continuous ML score (0–99) → bucketed risk level → deterministic rules layer referencing the score → reviewable queue with explanations. This is precisely the two-stage architecture our proposal generalizes to agent actions. *Remaining difference*: Radar's score is **single-dimensional** (one fraud-likelihood probability), not a multi-dimensional vector across 11 orthogonal risk types; it is closed, proprietary, and domain-specific to payments, with no public evidence anyone has ported this exact architecture to agent tool calls.

(Honorable mention: Microsoft Azure AI Content Safety's 5-category harm taxonomy — including an agent-specific "Task Adherence" dimension for misaligned tool invocations — is the closest thing to genuine multi-dimensionality found among the agent-firewall vendors, but every value is an uncalibrated ordinal severity bucket (0/2/4/6), not a probability, and Cisco AI Defense's 4-way classification array is the same shape with the same limitation.)

Everything else surveyed — the remaining agent-firewall vendors, all 10 MCP gateways, all 12 authorization/identity products — is deterministic rules/policy evaluation, categorical enum thresholds, binary detect-and-block, or identity/credential lifecycle management, none of which output a calibrated numeric probability of any kind, let alone a multi-dimensional one.

### Is there an OPEN (code + weights + data + recipe) pre-execution, per-action, multi-dimensional, calibrated risk classifier available today?

**No.**

Evidence:
- The only fully open-source, trajectory-aware, pre-execution interception project found — **Invariant Labs' Guardrails/mcp-scan/Explorer** (Apache-2.0, [github.com/invariantlabs-ai](https://github.com/invariantlabs-ai)) — is explicitly rule-based by its own documentation, not a trained/calibrated classifier, and ships no model weights or training recipe for risk scoring.
- The two vendors with the strongest "risk score" *language* (Noma Security, Prompt Security) are closed SaaS products with no published weights, training data, or calibration methodology, and neither scores individual tool calls across multiple orthogonal risk dimensions in the way our 11-dimension spec requires — they either score at the wrong granularity (MCP server, not action) or output categorical actions rather than probabilities.
- No cloud-native product exposes a calibrated per-action risk probability for tool calls: AWS Bedrock's content filters are enum strengths and explicitly exclude tool-call arguments; its one continuous score (contextual grounding, 0–0.99) targets output-hallucination-vs-source, not action risk, and is undocumented for calibration; Azure Content Safety and Cisco AI Defense both have genuinely multi-category schemas (5 harm categories incl. agent-specific Task Adherence; 4 violation classifications) but every value is boolean or ordinal-uncalibrated; Palo Alto's runtime scan API is a literal `malicious`/`benign` boolean; Google Model Armor uses 3-tier ordinal likelihood labels.
- No deterministic-authorization product (Oso, OpenFGA, Cedar/AVP, OPA, Permit.io, Auth0 for GenAI, WorkOS, Descope, Okta XAA, Astrix, Token Security, Britive) claims to produce a learned or calibrated risk probability — by design, and confirmed via official docs, these all answer "is this allowed," not "how risky is this."
- No vendor across either category publishes calibration evidence (reliability diagrams, Brier scores, or similar) for any risk-related score, open or closed.
- No vendor was found publicly using the "Stripe Radar for agent actions" framing, and Radar itself — the closest real-world architectural analog — is single-dimensional and proprietary.

This is a genuine, currently-unfilled niche: a **vendor-neutral, open, sequence-aware, calibrated, multi-dimensional pre-execution risk classifier for agent tool calls**, decoupled from the deterministic policy layer, does not exist today in open or closed form as of 2026-09-20.
