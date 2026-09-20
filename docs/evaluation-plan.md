# Evaluation plan

The evaluation suite is forecheck's primary scientific contribution. A held-out accuracy
number on synthetic data is the least interesting thing it produces. This document
defines what is measured, on what, against whom, and — most importantly — what each
number is and is not allowed to be called.

Implementation: `src/forecheck/evaluation/`. Every `EvaluationReport` carries a required
`evaluation_class` field; there is no default, so a report cannot be produced without
declaring which of the three classes it belongs to.

---

## 1. Three evaluation classes, kept separate

| Class | Data | What a good number means | What it does **not** mean |
|---|---|---|---|
| **1. Synthetic in-distribution** | `dev` / `test` splits: unseen families, seen tool families and templates | The model learned the label rules from the latent schema | Anything about real traffic |
| **2. Synthetic held-out-family and adversarial** | `heldout_family` (entire tool families withheld), `adversarial` (injection attempts against forecheck itself, paraphrase attacks, look-alikes) | The model generalizes across tool families and resists the attack shapes we thought of | Resistance to attack shapes we did not think of |
| **3. External or human-labelled** | Adapted public benchmarks (evaluation-only), the human gold set once it exists | Something about the world | — |

Numbers from different classes are never averaged, never plotted on one axis, and never
reported without the class named. Reports for classes 1 and 2 print, verbatim:
*"Synthetic data. No real-world safety claim is made."*

Until a class-3 result exists, the README, model card and any external communication
describe forecheck's performance as *synthetic* and make no real-world safety claim.

## 2. Ground truth and what counts

Labels are `yes` / `no` / `not_applicable` / `undetermined` per dimension (ADR 0003).
**`not_applicable` and `undetermined` cells are excluded** from every per-dimension
metric. They are never counted as negatives, because doing so inflates precision on
rare positives and rewards a model for scoring the irrelevant dimension low. Every
metric reports `n_evaluable`; a dimension with `n_evaluable = 0` reports no metric, not
a perfect one.

## 3. Metrics

### 3.1 Per dimension
Precision, recall, F1 at a stated threshold; AUPRC (the primary ranking metric, because
positives are rare on most dimensions); AUROC (secondary). The F1-optimal threshold is
found on the `dev` split and applied to `test`; it is never searched on the split being
reported.

### 3.2 Aggregates
Macro over the eleven dimensions. **Worst slice**: the minimum over all slices of the
chosen metric, reported beside the macro. A model that is excellent on average and
useless on `hr_identity` is useless.

### 3.3 Calibration
Brier score, negative log-likelihood, expected calibration error (15 equal-width bins),
adaptive ECE (equal-mass bins), and reliability diagrams per dimension. Reported for
raw scores *and* for calibrated probabilities, so the effect of the calibration artifact
is visible. Calibration metrics are computed on `test`, never on the `calibration`
split the artifact was fitted on.

### 3.4 Decision layer
Run through a named policy bundle:

- **False-allow rate**: examples with a positive high-severity label (exfiltration,
  irreversible, escalation, injection-driven mutation) that the bundle `ALLOW`ed.
- **False-deny rate**: benign hard negatives that the bundle `DENY`ed.
- **Review rate**: the human-workload cost.
- **Risk-weighted cost**: a stated cost matrix (default: false-allow on irreversible or
  exfiltration = 10, other false-allow = 3, false-deny = 1, review = 0.2). The matrix is
  a parameter and is printed in the report; the default is an opinion, not a finding.

Ground truth for "should have been denied" comes from labels via a documented mapping,
never from the engine under test.

### 3.5 Selective prediction
Risk–coverage curve and AURC using `|p − 0.5|` as confidence, and separately using
`insufficient_context` as the abstention signal. Selective accuracy at coverage 50 / 70
/ 80 / 90 / 100 %. This is how abstention is evaluated: does declining to answer buy
accuracy on what remains?

### 3.6 Contrastive consistency and invariance
Over contrastive pairs (`contrastive_pair_id`):

- **Pair consistency** — for each non-invariant axis, the fraction of pairs where the
  score on the targeted dimension moves in the direction the label delta requires, and
  the mean signed delta.
- **Counterfactual sensitivity** — mean |Δp| on dimensions whose label flipped.
- **Invariance** — for `surface_paraphrase` pairs, mean |Δp| across all dimensions, and
  the fraction of pairs where any dimension moves more than 0.05.

These three catch the failure that headline accuracy hides: a model keying on surface
text rather than on the causal fact. A model can have high AUPRC and fail all three.

### 3.7 Slices
By tool family; by difficulty tier; by contrastive axis; by trajectory length (0, 1–3,
4–10, 11+); by benign-hard-negative flag; by number of context gaps; by rendered-context
length; by policy present vs absent; by **out-of-domain tool** (tool name absent from
the training tool set); by unseen policy predicate kind. Multilingual and paraphrase
slices are added when the LLM renderer produces them; the offline template renderer
produces English only and the report says so.

### 3.8 Trajectory versus isolated action
The same latent scenario rendered with and without its trajectory, scored on
`suspicious_action_sequence` and on the consequence dimension. Measures whether the
model actually uses the trajectory or ignores it.

### 3.9 Performance
p50 / p90 / p99 latency, throughput, peak RSS; sliced by rendered-context length and by
number of dimensions requested; hardware string recorded. Mock and real backends are
never reported in the same table without the backend named in every row.

### 3.10 Uncertainty
Every headline metric carries a 95 % bootstrap confidence interval (1000 resamples over
examples, stratified by family, fixed seed). Differences between systems whose intervals
overlap are reported as "not distinguished at this sample size", not as wins.

## 4. Baselines

All baselines score the same examples with the same candidate-logit interface where
applicable, so differences are attributable to the model and not to the scoring path.

| Baseline | What it tells us | Requires |
|---|---|---|
| Deterministic rule baseline (`RuleBaselineBackend`) | How far typed facts alone get you — the floor a learned model must beat | nothing |
| Untuned base model, same candidate-logit scoring | Whether fine-tuning did anything | the base model |
| Bespoke Nimble base (Apache-2.0 weights) | Whether an open general-purpose structured classifier already matches us on our schema | ~9B model, GPU; its code licence to be confirmed before any adapter is shipped |
| Generative LLM judge (per-dimension yes/no prompt) | Whether the small specialised model beats a large general one, and at what latency | an API key; optional; never in default tests |
| TypeSafe Jev (optional adapter) | Same, for the closest hosted product | an API key and a ToS review; optional |
| Prompt-injection detector (DeBERTa-class) on the `prompt_injection_influence` dimension only | Whether provenance-aware scoring beats text-only detection on the one dimension they share | the model weights |

The default test suite requires none of the optional rows.

## 5. Public benchmarks: what can and cannot be adapted

Full licence matrix and per-benchmark mapping analysis in
[`research-landscape.md`](research-landscape.md) §6. Summary of the position taken:

- **Evaluation-only, enforced.** AgentHarm (no-train clause + canary), OS-Harm (canary),
  TraceSafe (maintainer statement), PrivacyLens (maintainer request) are ingested, if at
  all, with `SourceLicense.usage = eval_only` and are refused by the training and
  calibration loaders. This is a code check, not a convention.
- **Not ingested.** R-Judge (no licence file), BrowserART (contradictory licences; the
  restrictive one is binding).
- **Shortlist for class-3 adaptation**, in order: TraceSafe (step-level, closest
  structure), ST-WebAgentBench (the only source with an organizational policy
  hierarchy), InjecAgent (deterministic single-action injection labels). Each maps to
  a *subset* of dimensions — typically `prompt_injection_influence` plus one
  consequence — and the adaptation reports only those dimensions, with the unmapped
  ones marked `not_applicable`. Forcing a benchmark's binary "attack succeeded" label
  onto eleven dimensions would be a fabrication and is not done.
- **No public benchmark supplies identity, delegated permissions or organizational
  policy as structured inputs.** Adapted examples therefore carry
  `insufficient_context`-inducing gaps by construction, and their scores on
  `unauthorized_scope` and `policy_conflict` are not meaningful. The report marks them
  `not_applicable` rather than reporting a number.

## 6. Human-labelled gold set

Protocol and annotation format are in `docs/annotation-protocol.md` (to be written
alongside the first annotation round; the JSONL format is the `Example` record with
`provenance.generator_name = "human"` and per-annotator label sets). Requirements
already fixed:

- Two independent annotators per example; adjudication on disagreement; Cohen's κ
  reported per dimension.
- Annotators see the same `ActionContext` the model sees, and label the eleven
  dimensions descriptively using the `LABEL_DERIVATION_RULES` text as the rubric — so
  human labels and synthetic labels answer the same question.
- Examples drawn from real (consented, redacted) agent traces where possible, otherwise
  from adapted benchmarks; never from forecheck's own synthetic generator.
- The gold set is a class-3 evaluation set only. It is never used for training or
  calibration.

## 7. What is reported where

| Artefact | Contains | Class |
|---|---|---|
| `reports/<run>/report.json`, `report.md` | Everything in §3 for one backend on one split | Stated per report |
| Model card | Class 1 and 2 numbers, clearly labelled synthetic; class 3 when it exists | All, separated |
| README | A pointer to the model card; no numbers | — |

## 8. Fixed seeds

Data generation, splitting, bootstrap resampling and the mock backend's jitter are all
seeded; the seed appears in every report. Two runs with the same seed and the same code
produce byte-identical reports. A test asserts this for the mock backend on the fixture
set.
