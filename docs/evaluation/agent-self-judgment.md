# Agent self-judgment vs external checker

This evaluation answers a question forecheck's own metrics do not: if the acting agent
is simply asked to judge its own proposed action, how well does that compare to
routing the same action through a trained external checker? `--backend agent_self`
(`src/forecheck/inference/agent_self.py`) feeds the same examples used to evaluate
forecheck's classifier (`forecheck evaluate --backend hf`) to an instruct model
(default `ibm-granite/granite-3.3-8b-instruct`) wrapped in a Fin-style
customer-service-agent system prompt, carrying the same principal entitlements,
delegated scopes, and policy text the classifier sees, then the pending tool call, and
reads one PROCEED/STOP verdict off it.

## Why one scalar instead of eleven dimensions

forecheck's trained backends (`hf`, `encoder`) and the zero-shot guardian baselines
each answer all eleven `RiskDimension` questions independently per example. A
production agent does not know this taxonomy: it only decides whether to act. So
`AgentSelfBackend` produces a single `p_stop` per example — read off the softmax over
the first output token's STOP vs PROCEED logits, exactly as `forecheck.inference.hf`
reads yes/no — and copies that one score to every dimension's raw score.

Scoring the same scalar against all eleven dimensions' labels is deliberate, not a
shortcut: it measures how much of each dimension's risk a single blanket
act/refuse decision happens to cover. A dimension where the agent's AUPRC is close to
the classifier's says "this risk is visible enough that a single top-level decision
catches it too"; a dimension where the agent badly lags says "this risk needs
dimension-level structure an undifferentiated verdict cannot express" — evidence for
keeping an external, multi-dimensional checker in the loop rather than trusting the
acting agent's own judgment.

## How to read the report

Running `forecheck evaluate --backend agent_self ...` produces the same
`report.json`/`report.md` as any other backend, plus a `## Self-judgment vs external
checker` section listing, per dimension, the agent's AUPRC and recall@selected
(recall at the F1-optimal threshold selected on a disjoint split, per
`evaluation.metrics.find_f1_optimal_threshold`). Passing `--compare-report
<path/report.json>` (a forecheck classifier report evaluated on the *same* split) adds
the checker's AUPRC/recall alongside the agent's and the delta (agent − checker); a
negative delta means the checker outperforms the agent on that dimension.

`--dump-n N` additionally greedily generates a verdict and short JSON reason for the
first `N` examples and writes them to `agent_self_dump.jsonl` next to the report, for
qualitative spot-checking. This generation path is never used for scoring.

## Threats to validity

- **The prompt is ours, not Fin's.** `_system_prompt` in `agent_self.py` is a
  reasonable customer-service-agent framing we designed for this comparison, not
  Intercom's actual production Fin prompt. A different system prompt (more or less
  cautious phrasing, different tool-call framing, few-shot examples) could move the
  agent's PROCEED/STOP boundary substantially. Treat results as a lower/upper bound on
  what a *reasonably prompted* agent could do, not a claim about Fin specifically.
- **Synthetic data.** Like every other class 1/2 report in this suite (see
  `docs/evaluation-plan.md` §1), the underlying examples are synthetic. A model that
  looks well-calibrated here may not generalize to real conversation distributions.
- **One decision, eleven labels.** By design (see above) the same `p_stop` is scored
  against every dimension. A high AUPRC on, say, `financial_commitment` does not mean
  the agent is reasoning about financial risk specifically — it may simply correlate
  with whatever made the agent say STOP for unrelated reasons on the same examples.
  Do not read per-dimension numbers here as evidence of dimension-specific reasoning.
- **Model choice affects the comparison.** The 8B config uses the same base as our
  training experiments generally target (`configs/training/8b.yaml`); the 2B config
  uses the exact base our trained classifier LoRA-adapts
  (`configs/training/2b.yaml`), which is the fairer head-to-head since it isolates
  "trained checker" vs "same base model, prompted instead of trained" from "different
  base model capability".
- **Greedy candidate-token scoring vs free-form deployment.** Real deployments would
  likely let the agent reason before deciding; here `p_stop` is read directly off the
  first output token to keep scoring deterministic and comparable to the other
  backends, which may understate what a longer chain-of-thought agent could do.
