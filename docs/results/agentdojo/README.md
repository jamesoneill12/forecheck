# AgentDojo external transfer results (2026-09-22)

forecheck's first result on data we did not generate. AgentDojo (Debenedetti et al.
2024, MIT licence) publishes agent run traces for its banking suite: two models,
claude-3-5-sonnet-20241022 and gpt-4o-2024-05-13, 1,714 runs, 4,215 proposed tool
calls, 11 attack types plus the no-attack runs. Trace parsing and label derivation
are documented in `docs/external-agentdojo.md`; the derivation version used here is
`agentdojo-1.2.0`. That doc's "Rendering channels" section records the render-v1
lesson: the first export left injected text only in the trajectory summary, and the
2B checker scored below the base rate on `prompt_injection_influence` for a
rendering reason, not a checker reason. `docs/plan-external-benchmark-port.md`
covers why AgentDojo was chosen over InjecAgent, AgentHarm and ToolEmu.

Labels come from AgentDojo's own `ground_truth()` functions, not from forecheck's
generator. `prompt_injection_influence` is `yes` when a call executes the injection
task's goal, matched on the attacker's target identifier; positive rate 0.150 over
4,133 evaluable calls, with 82 calls in no-injection runs marked `not_applicable`.
`unauthorized_scope` is `yes` when the call's function is outside the user task's
reference-solution function set; rate 0.253. `policy_conflict` is `yes` when one of
four banking policies we wrote once per suite fires, checked by deterministic
predicates; rate 0.237. `financial_commitment` (0.343) and
`destructive_or_irreversible_action` (0.097) come from function-name sets.
`untrusted_destination` has positives only, 1,447 of 4,215, so AUPRC is undefined
and it is dropped from the macro. `privilege_escalation`, `insufficient_context`,
`sensitive_data_exposure`, `suspicious_action_sequence` and
`external_communication` have no ground truth on this suite and are
`not_applicable` throughout.

All arms below are zero-shot. Nothing was trained or tuned on AgentDojo: the
checkers are the v4 synthetic-trained models, the calibration bundles were fitted
on synthetic dev, and threshold selection is disabled (`--threshold-split none`).
Reports: `rule-baseline-report.md`, `decoder-2b-v4-report.md`,
`decoder-2b-v4-strip-report.md` (eval-time `--strip-identity`),
`decoder-2b-v4-noid-report.md` (train-time stripped model, evaluated stripped),
`decoder-8b-v4-report.md`, `decoder-8b-v4-strip-report.md`,
`decoder-{2b,8b}-v6-report.md` and `decoder-{2b,8b}-v6-strip-report.md` (v6 =
leak-free generator, `../notes/injection-label-leak-diagnosis.md`),
`guardian-3.3-8b-report.md`, `agent-self-8b-report.md`. render-v1 reports, the
first export before the rendering fix, are under `render-v1/`.

## Results

AUPRC / AUROC, with the positive rate in the column header. n=4,215 for every
dimension except `prompt_injection_influence`, n=4,133.

| arm | prompt_injection_influence (0.150) | unauthorized_scope (0.253) | policy_conflict (0.237) | financial_commitment (0.343) | destructive (0.097) | macro AUPRC | macro ECE |
|---|---|---|---|---|---|---|---|
| rule baseline | 0.250 / 0.737 | 0.253 / 0.500 | 0.237 / 0.500 | 0.896 / 0.921 | 1.000 / 1.000 | 0.527 | 0.250 |
| decoder 2B v4 | 0.128 / 0.348 | 0.257 / 0.481 | 0.849 / 0.937 | 1.000 / 1.000 | 1.000 / 1.000 | 0.647 | 0.200 |
| decoder 2B v4, eval-stripped | 0.125 / 0.292 | 0.218 / 0.409 | 0.694 / 0.849 | 1.000 / 1.000 | 1.000 / 1.000 | 0.608 | n/a (raw margins, no bundle) |
| decoder 2B v4 train-stripped | 0.150 / 0.475 | 0.234 / 0.426 | 0.390 / 0.660 | 1.000 / 1.000 | 1.000 / 1.000 | 0.555 | 0.203 |
| decoder 8B v4 | 0.701 / 0.895 | 0.355 / 0.506 | 0.626 / 0.912 | 0.923 / 0.922 | 0.999 / 1.000 | 0.721 | 0.254 |
| decoder 8B v4, eval-stripped | 0.743 / 0.915 | 0.266 / 0.523 | 0.404 / 0.787 | 0.934 / 0.936 | 1.000 / 1.000 | 0.669 | n/a (raw margins, no bundle) |
| decoder 2B v6 (leak-free generator) | 0.693 / 0.928 | 0.214 / 0.356 | 0.670 / 0.905 | 0.935 / 0.934 | 1.000 / 1.000 | 0.702 | 0.260 |
| decoder 2B v6, eval-stripped | 0.669 / 0.921 | 0.306 / 0.633 | 0.521 / 0.862 | 0.941 / 0.944 | 1.000 / 1.000 | 0.687 | n/a (raw margins, no bundle) |
| decoder 8B v6 (leak-free generator) | 0.838 / 0.966 | 0.239 / 0.452 | 0.785 / 0.943 | 0.945 / 0.956 | 0.831 / 0.977 | 0.728 | 0.256 |
| decoder 8B v6, eval-stripped | 0.819 / 0.960 | 0.354 / 0.661 | 0.450 / 0.817 | 0.979 / 0.987 | 0.975 / 0.998 | 0.715 | n/a (raw margins, no bundle) |
| Granite Guardian 3.3 8B zero-shot (n=1000) | 0.103 / 0.233 | 0.289 / 0.494 | 0.224 / 0.450 | 0.257 / 0.237 | 0.217 / 0.697 | 0.218 | 0.275 |
| agent-self 8B, ALLOW/STOP (n=1000) | 0.291 / 0.775 | 0.442 / 0.734 | 0.449 / 0.792 | 0.591 / 0.804 | 0.105 / 0.580 | 0.375 | 0.398 |

## Reading

1. **Policy checking transfers.** 2B v4 zero-shot scores 0.849 AUPRC on
   `policy_conflict` against a 0.237 base rate and a rule baseline at base rate,
   on policies it never saw, in a tool schema it never saw, on traces produced by
   other people's agents. Eval-time stripping drops it to 0.694 and the
   train-time stripped model to 0.390. That is the same identity dependence
   found on synthetic data (`docs/results/synthetic-v2/README.md`, identity
   ablation), now confirmed on external data.

2. **Injection transfer on v4 was a data effect, not a scale effect.** 2B v4
   fails outright: 0.128 AUPRC, below the 0.150 base rate, AUROC 0.348. 8B v4
   gets 0.701 AUPRC and 0.895 AUROC zero-shot. The rule baseline sits between
   the two, 0.250 / 0.737, because presence of untrusted content is a strong
   but insufficient cue. (An earlier 8B v4 run reported 0.797 / 0.916 and was
   quoted in earlier versions of this README and the paper. Two later runs on
   the current export, with per-example scores identical to each other, give
   0.701 / 0.895; we could not reproduce the earlier number and report the
   reproducible one.) The v6 checkers, trained on the leak-free generator
   (`../notes/injection-label-leak-diagnosis.md`), change the picture: 2B v6
   reaches 0.693 / 0.928 and 8B v6 0.838 / 0.966, so the 2B failure was the
   generator's leak, not the model's size. On the dump, the 2B v6 injection
   head fires: median raw logit +4.5 for positives against -3.0 for negatives,
   92% of positives above 0 against 23% of negatives; 8B v6 is +6.25 vs -3.25,
   94% vs 8%. Eval-time identity stripping barely moves either (0.669 and
   0.819), so the head is reading content. The 2B v4 result
   is a plain failure, and the per-example dump (`--dump-scores`, job
   `eval-agentdojo-diag`) says why: the 2B injection head never fires on this
   domain. Raw logits for all 4,133 evaluable calls lie between -5.0 and -3.0;
   the highest-scoring positive is -3.25 and no row scores above 0. The
   ordering that remains is noise, slightly inverted because calls with a
   prior tool result score a quarter-logit lower than first calls. By contrast
   the 2B `policy_conflict` head separates cleanly on the same rows (median raw
   +2.5 for positives, -3.5 for negatives). The 2B model learned injection from
   surface cues of the synthetic generator that AgentDojo's injections do not
   carry; 8B v4 learned something that partly transfers. The 8B v4 dump shows
   the head is live but shifted: median raw -1.75 for positives vs -3.50 for
   negatives, and 29% of positives score above 0 against 0.7% of negatives, so
   the ranking is partly right while most true positives sit below the decision
   boundary, which is the ECE 0.254 in one number. The same dump explains `unauthorized_scope`:
   8B scores above 0 on 77% of negatives and 66% of positives (both medians
   +6.75), i.e. the head fires on almost everything and carries no signal on
   this label. The two 8B baselines separate
   scale from training: the same Granite-3.3-8B base asked ALLOW/STOP as the agent
   scores 0.291 / 0.775 on injection, and Granite Guardian 3.3 8B zero-shot scores
   0.103 / 0.233, below base rate. The trained checkers' 0.70 to 0.84 is
   therefore the training, not the parameter count.
   Stripping identity from the 8B v4 input keeps injection (0.743 / 0.915) and drops
   `policy_conflict` from 0.626 to 0.404, the same split between content and
   identity dimensions the synthetic identity ablation showed; 8B v6 shows the
   same split (0.785 to 0.450).

3. **`unauthorized_scope` does not transfer.** 0.257 (2B v4), 0.355 (8B v4),
   0.214 (2B v6) and 0.239 (8B v6) AUPRC
   against a 0.253 base rate is chance to marginal. The label itself is the
   weakest one here: "function not in the reference solution" counts harmless
   auxiliary reads as out of scope, as noted in the "Known gaps" section of
   `docs/external-agentdojo.md`. We report this number and do not claim
   transfer on it.

4. **The 8B-below-2B `policy_conflict` gap is not robust.** On v4, 8B scores
   0.626 AUPRC against 2B's 0.849 while its AUROC (0.912) stays high. On v6 the
   order reverses: 8B 0.785, 2B 0.670. A second 8B v4 seed on synthetic
   `heldout_policy_kind` gives `policy_conflict` 0.825 against seed 0's 0.851,
   so single-seed differences of 0.03 on this dimension are noise there, but
   the v4 AgentDojo gap of 0.22 is larger than that. With one seed per (size,
   data version) cell we cannot say more than that the direction flips with
   the training data; the AUROCs (0.91 to 0.94) agree that both sizes rank
   the policy violations well and differ in how many benign calls they put
   above them.

5. **Calibration does not transfer, but an in-domain refit fixes it.** Macro ECE runs 0.20 to 0.27 for the
   calibrated arms here, against under 0.03 on synthetic data. Calibration must
   be refit on in-domain data: the ranking transfers, the probabilities do not.

   Refitting per-dimension isotonic calibrators on half of the AgentDojo calls
   and testing on the other half brings macro ECE to 0.008 (2B) and 0.010 (8B)
   with AUPRC unchanged, and most of the gain arrives by 250-500 labelled
   calls (`docs/results/agentdojo/recalibration.md`,
   `scripts/agentdojo_recalibrate.py`).
6. **What this does and does not show.** This is one suite (banking), one
   domain, with labels partly written by us (the four policy predicates) and
   partly by AgentDojo (`prompt_injection_influence`, `unauthorized_scope`).
   The other three suites are in the next section.

## Four suites (banking, slack, travel, workspace)

Same export (`forecheck external agentdojo`, derivation `agentdojo-1.2.0`) over all
four AgentDojo suites for the same two agent models: 30,143 proposed tool calls
(banking 4,215, slack 8,246, travel 10,701, workspace 6,981). Positive rates fall
from banking to the rest: `prompt_injection_influence` 0.0985 overall (n=29,380
evaluable), `unauthorized_scope` 0.284, `policy_conflict` 0.0749. The banking
suite has four policies written against its tool schema; the other three suites
have one generic policy each, so `policy_conflict` outside banking is a weaker,
lower-base-rate label. Arms are the same zero-shot v4 checkers. Guardian and
agent-self are on a fixed 2,000-row subsample. Reports are under `all-suites/`;
per-suite numbers are in `all-suites/per-suite.md`.

AUPRC / AUROC, positive rate in the header. `destructive_or_irreversible_action`
and `financial_commitment` come from function-name sets and are not learned
signal. The v6 checkers were not run on the four-suite export.

| arm | prompt_injection_influence (0.099) | unauthorized_scope (0.284) | policy_conflict (0.075) | financial_commitment (0.054) | destructive (0.029) | macro AUPRC |
|---|---|---|---|---|---|---|
| rule baseline | 0.129 / 0.630 | 0.591 / 0.714 | 0.075 / 0.500 | 0.765 / 0.876 | 1.000 / 1.000 | 0.512 |
| decoder 2B v4 | 0.098 / 0.498 | 0.676 / 0.688 | 0.519 / 0.832 | 0.999 / 1.000 | 1.000 / 1.000 | 0.659 |
| decoder 8B v4 | 0.490 / 0.845 | 0.350 / 0.615 | 0.540 / 0.954 | 0.840 / 0.953 | 1.000 / 1.000 | 0.644 |
| decoder 8B v4, eval-stripped | 0.498 / 0.845 | 0.396 / 0.645 | 0.188 / 0.816 | 0.820 / 0.937 | 1.000 / 1.000 | 0.580 |
| Granite Guardian 3.3 8B (n=2000) | 0.116 / 0.553 | 0.310 / 0.570 | 0.073 / 0.475 | 0.091 / 0.639 | 0.069 / 0.717 | 0.132 |
| agent-self 8B ALLOW/STOP (n=2000) | 0.251 / 0.809 | 0.461 / 0.727 | 0.203 / 0.833 | 0.150 / 0.815 | 0.067 / 0.754 | 0.227 |

Per suite, `prompt_injection_influence` AUPRC / AUROC (positive rate):

| arm | banking (0.150) | slack (0.186) | travel (0.025) | workspace (0.077) |
|---|---|---|---|---|
| rule baseline | 0.250 / 0.737 | 0.222 / 0.601 | 0.021 / 0.360 | 0.138 / 0.740 |
| decoder 2B v4 | 0.128 / 0.348 | 0.178 / 0.479 | 0.048 / 0.686 | 0.065 / 0.353 |
| decoder 8B v4 | 0.701 / 0.895 | 0.433 / 0.738 | 0.131 / 0.834 | 0.752 / 0.941 |
| decoder 8B v4, eval-stripped | 0.743 / 0.915 | 0.421 / 0.726 | 0.146 / 0.844 | 0.727 / 0.943 |
| agent-self 8B | 0.354 / 0.832 | 0.292 / 0.687 | 0.026 / 0.484 | 0.246 / 0.866 |

Reading:

1. **The 8B v4 injection transfer holds on three of four suites.** Full-context
   8B is at 0.70 / 0.90 on banking, 0.75 / 0.94 on workspace, 0.43 / 0.74 on
   slack, each several times the base rate, and the eval-stripped arm is within
   0.04 of it everywhere; travel is 0.13 AUPRC at a 0.025 base rate with AUROC
   0.83, so the ranking is right but positives are rare and the head fires on
   many benign travel calls. 2B is at base rate on every suite, which is
   the same failure as banking. Given the InjecAgent result
   (`../injecagent/README.md`), what transfers here is call-level: the attacker's
   call is one the user did not ask for.
2. **`unauthorized_scope` is mostly a rule-baseline effect outside banking.** The
   rule baseline scores 0.749 / 0.759 on slack and 0.733 / 0.755 on workspace,
   where the base rate is 0.46 to 0.48; 2B adds 0.04 to 0.09 AUPRC on top, and 8B
   eval-stripped is below the rule baseline on both. AgentDojo's label (function
   not in the reference solution) counts auxiliary reads as out of scope, and on
   slack and workspace nearly half of all calls are labelled positive, so this is
   not a label we claim transfer on.
3. **`policy_conflict` outside banking is a weak label and the numbers say so.**
   Banking has four policies that name specific tools and recipients and 2B
   reaches 0.849 there. Slack, travel and workspace have one generic policy each
   with base rates of 0.7 to 8 percent; 2B scores 0.196 / 0.776 on slack, 0.493 /
   0.892 on workspace and nothing on travel (0.005, 7 positives per thousand).
   The AUROCs above 0.8 mean the head is ordering correctly; the AUPRCs mean the
   positive is too rare and the policy too vague to separate well. Writing
   suite-specific policies for the three suites is the fix; we did not do it
   before submission.
4. **Baselines.** Guardian is at or below base rate on every dimension on every
   suite. Agent-self has real signal on injection (0.25 / 0.81 overall, 0.35 /
   0.83 on banking) and on `policy_conflict` AUROC (0.83), below the trained
   checkers on AUPRC everywhere except slack injection where it ties.
5. **Macro AUPRC moves against 8B here because of the label mix.** 2B (0.659)
   beats 8B (0.644) and 8B eval-stripped (0.580) on the macro because 2B carries
   `unauthorized_scope` and `policy_conflict` through the rule-like and identity
   cues, while 8B carries injection. Read the dimension columns, not the macro.

## Compared with render-v1

render-v1 (`render-v1/`) left tool results only in `trajectory.result_summary`,
truncated to 500 characters, with no observations channel, and derived
`destination.trust` from the label itself. Rule baseline macro AUPRC there was
0.510. 2B v4 scored injection 0.140 / 0.453, `unauthorized_scope` 0.302 / 0.512,
`policy_conflict` 0.860 / 0.937, macro 0.660. 2B eval-stripped scored injection
0.130 / 0.351, `policy_conflict` 0.711 / 0.862. Moving the injected text into the
observations channel for the current export changed nothing for 2B on injection
(0.140 to 0.128), so the 2B failure is not a channel artefact. 8B was not run on
render-v1.

## Next

- Find which synthetic cue the 2B injection head keys on (ablate observation
  source names, `attacker.example` domains, the "Note to assistant" phrasing) and
  diversify the generator's injection templates so 2B transfers too.
- Write suite-specific policies for slack, travel and workspace so
  `policy_conflict` there is as sharp a label as on banking.
- Score the v6 (leak-free) checkers on all four suites.
- A second seed per (size, data version) cell to settle the `policy_conflict`
  size question.
