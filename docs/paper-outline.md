# Workshop paper outline

Status: outline only, no draft prose beyond the abstract. All numbers below are taken
verbatim from `docs/results/synthetic-v2/README.md`, `docs/evaluation/approval-elimination.md`,
`docs/adr/0010-policy-generalisation-splits.md`, and `docs/evaluation/multi-policy-stacking.md`.
Anywhere a number does not yet exist, this outline says `pending (v3/v4 job)` rather
than inventing one.

## Working title

**"Identity Is the Signal: Why Pre-Execution Agent-Action Risk Needs Delegated Authority,
Not Just Content"**

Alternates considered: "What Guardrail Models Don't See: Identity-Conditioned Risk for
Agent Tool Calls"; "Calibration, Not Consensus: Composable Multi-Policy Risk Scoring for
AI Agents."

## Abstract draft (~150 words)

Guardrail models for AI agents typically classify a proposed action from its text
alone. We show this misses the dimensions that matter most for delegated, tool-using
agents. Stripping principal entitlements, delegated scopes, and policy text from a
trained 2B-parameter decoder's input drops macro AUPRC from 0.915 to 0.736 on held-out
tools, concentrated entirely in three dimensions — unauthorized-scope detection falls
from 1.00 to 0.12, policy-conflict detection from 1.00 to 0.35 — while two zero-shot
safety models (Granite Guardian 3.3 8B, gpt-oss-safeguard 20B) sit at chance on exactly
these dimensions with or without that context, showing the gap is not something
prompting a general safety model can close. We further show that the *shape* of
policy-conditioned reasoning, not just tool identity, must generalize to unseen policy
kinds and phrasings, and that naive multi-policy composition collapses to a 0.97 false
positive rate by three stacked policies unless decisions are made from calibrated joint
probabilities rather than independent thresholds. All results are on synthetic data;
we are explicit about what that does and does not license.

## Section list

1. **Introduction.** Key claim: agent-action risk is not one classification problem but
   two — content risk (does this look dangerous) and authorization risk (was this agent
   allowed to do this, by this principal, for this task) — and existing guardrail
   models only address the first. Figure: two-panel schematic, content-risk model vs.
   authorization-risk model, showing what each has access to (text only vs. text +
   entitlements + delegated scopes + policy).

2. **Problem setting and contract.** Key claim: a pre-execution risk classifier needs a
   typed contract carrying principal entitlements, agent delegated scopes, trust-labelled
   observations, and policy text as first-class fields, not prose the model must parse
   unassisted. Figure/table: the `ActionContext` schema (`src/forecheck/contracts/context.py`)
   as a field table, mapped to the 11 `RiskDimension`s it feeds.

3. **The eleven risk dimensions.** Key claim: dimensions split cleanly into
   content/consequence dimensions (destructive, financial, external communication,
   untrusted destination, sensitive data exposure — largely determined by typed facts)
   and delegated-authority dimensions (unauthorized scope, policy conflict, insufficient
   context — determined by the relationship between identity, delegation, and policy).
   Table: the 11 dimensions with one-line definitions from `src/forecheck/contracts/enums.py`,
   annotated content vs. delegated-authority.

4. **Identity ablation (Result a).** Key claim: three dimensions collapse to chance when
   identity/policy context is removed, and a deterministic rule baseline cannot recover
   them either, so the failure is informational, not architectural. Table: per-dimension
   heldout AUPRC, decoder full vs. identity-stripped vs. rule baseline
   (`unauthorized_scope` 1.000/0.116/0.512; `policy_conflict` 0.999/0.345/0.315;
   `insufficient_context` 0.849/0.418/0.235; macro 0.915/0.736/0.614). Figure: bar chart
   of the same three dimensions for decoder-full, decoder-stripped, ModernBERT-full,
   ModernBERT-stripped, Granite Guardian, Granite Guardian-stripped, gpt-oss-safeguard,
   showing zero-shot models flat near chance in every column while the trained decoder's
   bar drops sharply only when stripped.

5. **Zero-shot safety models are at chance on delegated authority (Result a, cont.).**
   Key claim: this is not a fine-tuning-vs-prompting gap closable by better prompting
   alone — Granite Guardian 3.3 8B (macro AUPRC ~0.243–0.257) and gpt-oss-safeguard 20B
   (~0.269, ~50x slower per row) are near chance on `unauthorized_scope` and
   `insufficient_context` specifically, and stripping identity does not hurt them
   (sometimes slightly helps), showing they never used it. Table: per-dimension AUROC/AUPRC
   for both zero-shot models, full vs. stripped, next to the trained decoder for scale.

6. **Held-out-policy generalization (Result b).** Key claim: robustness to unseen tools
   is not the same claim as robustness to unseen *policy kinds* or unseen *policy
   phrasings* — the latter is the harder, more product-relevant generalization test
   (ADR 0010), and passing it requires having learned to *read* a policy clause rather
   than pattern-match on eight fixed clause templates. Table: encoder granite-embedding-r2
   v3 macro AUPRC and `policy_conflict` AUPRC across test / heldout_family /
   heldout_policy_kind / heldout_policy_phrasing (0.828/0.833/0.848/0.832 macro;
   `policy_conflict` 0.451/0.441/0.441/0.467 — flat because the encoder never learned the
   dimension, ~chance at a 0.36–0.41 positive rate). Decoder 2B v3 numbers on the same
   splits: `pending (v3/v4 job)`. Figure: four-way bar chart of `policy_conflict` AUPRC
   across the four splits for encoder vs. decoder (decoder bars marked pending).

7. **Multi-policy composition (Result c).** Key claim: threshold-based composition of
   independently reasonable single-policy guards is not itself reasonable at scale — it
   compounds toward "deny everything" purely as a function of how many policies are
   stacked, independent of any policy or guard getting worse — and this is fixable only
   by deciding from the joint calibrated probability vector, not by better rule
   engineering. Table: decoder 2B stacking results, k=1/2/3/8, independent vs. joint vs.
   expected_cost_joint FPR (0.015 → 0.140/0.905 → **0.966**/0.905 → 0.966, vs.
   expected_cost_joint flat at 0.082 from k=2 on). Figure: FPR vs. k, three lines
   (independent, joint, expected_cost_joint) for the decoder, plus the same three lines
   for the granite-embedding-r2 encoder to show the invariance property degrades
   (encoder expected_cost_joint FPR 0.921, not flat/low) when probabilities are not
   sharply calibrated.

8. **Why calibration is the hinge, not the policy engine.** Key claim: expected-cost
   composition's k-invariance is a property of the *model's* calibration quality
   (decoder ECE 0.004, ~well-calibrated) interacting with a fixed decision rule, not a
   property of the decision rule alone — the same rule on flatter, less-calibrated
   probabilities (encoder ECE 0.049) does not stay low. Figure: reliability diagrams,
   decoder vs. encoder, side by side, annotated with the resulting stacking FPR at k=3
   for each.

9. **Limitations.** Must lead with: **synthetic data only** — every number in this
   paper is on data from forecheck's own generator (`docs/evaluation-plan.md` class 1/2),
   no human-labelled or production-traffic evaluation exists yet, and no real-world
   safety claim is made; **generator regularities** — the model may be exploiting
   template regularities in how the generator writes policy clauses and entitlement
   lists rather than a general policy-reading ability, which is exactly what the
   heldout-policy-kind/phrasing splits exist to probe and only partially rule out (the
   encoder result in §6 shows no drop, but it never learned the dimension in the first
   place, so that null result is uninformative); **privilege_escalation render defect**
   — `authority_before`/`authority_after` were not rendered into the tool call text in
   v2/v3 data, so every arm's 0.46–0.53 AUPRC on that dimension reflects a data defect,
   fixed for v4, not yet re-evaluated. Then: single generator family (English, template
   renderer only); cost table in §7–8 is a default severity-tier table, not tuned to any
   real organization; decoder 2B v3 policy-generalization numbers are pending at
   submission time.

10. **Related work.** Four buckets, positioned relative to Result (a)/(b): **LLM
    guardrails** (Llama Guard, Granite Guardian, gpt-oss-safeguard, ShieldGemma, Aegis)
    — general-purpose content/harm classifiers we show are at chance on
    delegated-authority dimensions specifically (§5), not a claim about their intended
    use. **Agent safety benchmarks** (AgentHarm, ToolEmu, InjecAgent, AgentDojo) — measure
    end-to-end agent behavior or injection success, not a per-action calibrated
    probability a policy engine can compose (§2, §7); none supply identity/delegation as
    structured input (`docs/evaluation-plan.md` §5). **Authorization/policy engines**
    (OPA/Cedar/XACML) — deterministic, symbolic, no learned uncertainty; forecheck's
    policy layer is architecturally in this family, but the composition problem in §7–8
    only exists because the input to that layer is now a probability, not a fact.
    **Calibration** — the composition result (§7–8) is a direct application of
    calibration literature to policy composition, which is not where that literature
    is usually pointed.

11. **Conclusion.** Key claim, restated: identity/delegation context and calibration
    quality are not incidental engineering details for agent guardrails — they are the
    two properties that determine whether a guardrail can (a) detect authorization
    violations at all and (b) survive being deployed alongside more than one policy.

## Figure/table inventory (compact)

| # | Section | Artifact |
|---|---|---|
| 1 | Intro | Two-panel schematic: content-risk vs. authorization-risk model inputs |
| 2 | Problem setting | `ActionContext` field table → 11 dimensions |
| 3 | Dimensions | 11-dimension table, content vs. delegated-authority tag |
| 4 | Identity ablation | Per-dimension heldout AUPRC table (3 dims) + 7-arm bar chart |
| 5 | Zero-shot chance | Per-dimension AUROC/AUPRC table, 2 zero-shot models, full vs. stripped |
| 6 | Policy generalization | 4-split macro/`policy_conflict` AUPRC table + bar chart (decoder pending) |
| 7 | Multi-policy stacking | k=1/2/3/8 FPR table + FPR-vs-k line chart, decoder + encoder |
| 8 | Calibration hinge | Reliability diagrams, decoder vs. encoder, annotated with stacking FPR |

## Length budget (8 pages)

Intro + problem setting ~1.5p, dimensions ~0.5p, identity ablation (§4–5) ~2p, policy
generalization (§6) ~1.5p, stacking + calibration (§7–8) ~1.5p, limitations ~0.5p,
related work ~0.75p, conclusion ~0.25p.
