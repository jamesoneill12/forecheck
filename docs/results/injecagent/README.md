# InjecAgent external results (2026-09-23)

Second dataset we did not generate. InjecAgent (Zhan et al. 2024, MIT licence) has
1,054 test cases: a user instruction, the user tool the agent calls for it, a tool
response template with a slot for an attacker instruction, and the attacker tool(s)
the instruction asks for (510 direct-harm cases, 544 data-stealing cases). The port
(`forecheck external injecagent`, `docs/external-injecagent.md`, derivation
`injecagent-1.0.0`) turns each case into a benign example (the user's own call, no
prior tool output) and, for each attacker tool, a **poisoned/clean pair**: the same
attacker call proposed after the tool response with the attacker instruction filled
in (`prompt_injection_influence=yes`) and after the same response with the slot
empty (`no`). Attacker-call arguments are identical within a pair, so the only
difference between a positive and its negative is whether the injected text is in
the untrusted observation. 4,250 examples: 1,054 benign, 1,598 poisoned, 1,598 clean.

Labels: `prompt_injection_influence` yes/no as above (`not_applicable` on benign
calls, which have no untrusted content); `unauthorized_scope` yes on every attacker
call (the delegated scope is the user tool only), no on benign; `policy_conflict`
from five generic policies with predicates we wrote once; `financial_commitment`,
`destructive_or_irreversible_action`, `untrusted_destination`,
`external_communication` from per-toolkit function-name sets;
`sensitive_data_exposure` yes on the data-stealing exfiltration call (its body is
the user's data), otherwise `not_applicable`. All arms zero-shot, v4 and v6 checkers,
synthetic calibration, `--threshold-split none`.

## Results

AUPRC / AUROC, positive rate in the header. n=4,250 except
`prompt_injection_influence` (n=3,196: the poisoned/clean pairs).

| arm | prompt_injection_influence (0.500) | unauthorized_scope (0.752) | policy_conflict (0.464) | financial_commitment (0.048) | destructive (0.144) | macro AUPRC |
|---|---|---|---|---|---|---|
| rule baseline | 0.500 / 0.500 | 0.752 / 0.500 | 0.464 / 0.500 | 0.683 / 0.833 | 1.000 / 1.000 | 0.680 |
| decoder 2B v4 | 0.549 / 0.596 | 0.732 / 0.493 | 0.965 / 0.971 | 1.000 / 1.000 | 1.000 / 1.000 | 0.849 |
| decoder 8B v4 | 0.544 / 0.529 | 0.849 / 0.691 | 0.977 / 0.980 | 0.734 / 0.931 | 1.000 / 1.000 | 0.821 |
| decoder 8B v4, eval-stripped | 0.556 / 0.545 | 0.843 / 0.642 | 0.968 / 0.973 | 0.766 / 0.967 | 1.000 / 1.000 | 0.827 |
| decoder 2B v6 (leak-free generator) | 0.878 / 0.865 | 0.704 / 0.376 | 0.922 / 0.914 | 0.970 / 0.999 | 0.998 / 1.000 | 0.894 |
| decoder 8B v6 (leak-free generator) | 0.943 / 0.936 | 0.677 / 0.369 | 0.965 / 0.963 | 0.771 / 0.967 | 0.997 / 1.000 | 0.870 |
| decoder 8B v6, eval-stripped | 0.953 / 0.949 | 0.917 / 0.786 | 0.963 / 0.965 | 0.839 / 0.984 | 0.998 / 1.000 | 0.934 |
| Granite Guardian 3.3 8B zero-shot (n=1000) | 0.511 / 0.537 | 0.613 / 0.147 | 0.359 / 0.293 | 0.102 / 0.724 | 0.197 / 0.588 | 0.356 |
| agent-self 8B ALLOW/STOP (n=1000) | 0.530 / 0.597 | 1.000 / 1.000 | 0.647 / 0.756 | 0.061 / 0.612 | 0.178 / 0.587 | 0.483 |

Paired view of the injection dimension (same attacker call, poisoned vs clean tool
output; 1,598 pairs, raw logits from `--dump-scores`):

| checker | poisoned scored higher | tie | median raw, poisoned | median raw, clean |
|---|---|---|---|---|
| 2B v4 | 0.504 | 0.239 | -3.75 | -4.25 |
| 8B v4 | 0.353 | 0.385 | -4.00 | -4.00 |
| 8B v4, eval-stripped | 0.382 | 0.397 | -4.00 | -4.00 |
| 2B v6 (leak-free generator) | 0.977 | 0.005 | +3.50 | -6.25 |
| 8B v6 (leak-free generator) | 0.977 | 0.012 | +2.25 | -3.50 |
| 8B v6, eval-stripped | 0.978 | 0.016 | +3.25 | -4.00 |

Reproduce with `scripts/injecagent_paired.py injecagent.jsonl NAME=scores.jsonl ...`.

## Reading

0. **The leak-free checkers read the injected text.** Retrained on the v6
   generator (`docs/results/notes/injection-label-leak-diagnosis.md`), 2B scores
   0.878 / 0.865 on `prompt_injection_influence` and 8B 0.943 / 0.936. With the
   call held fixed, both put the poisoned variant above its clean twin on 97.7%
   of the 1,598 pairs (ties 0.5% and 1.2%): 2B median raw +3.50 poisoned against
   -6.25 clean, 8B +2.25 against -3.50; 58% of poisoned calls score above 0 at
   both sizes, against 9% (2B) and 0.1% (8B) of clean. Same model sizes and
   recipes as the v4 rows, whose pair wins were 0.504 and 0.353. The readings
   below describe the v4 checkers and remain true of them; the cause they point
   to (the generator leak) is confirmed by its removal. `policy_conflict` also
   improves under v6 (0.922 / 0.965 against 0.965 / 0.977 for v4: unchanged
   within 0.04), and `unauthorized_scope` stays below base rate at both sizes.

1. **Neither v4 checker reads the injected text.** With the call held fixed, the
   presence of the attacker's instruction in the tool output moves the 8B injection
   score in the right direction on 35% of pairs and not at all on 39%; the 2B is at
   coin-flip. Both heads sit at raw logit -4 on poisoned and clean alike. This is
   the cleanest test we have of whether the checker's injection head reads the
   observation channel, and the answer for the v4 checkers is no.

2. **This reinterprets the AgentDojo injection result.** On AgentDojo the 8B
   checker separated the attacker's call from the benign calls in the same
   poisoned trace (AUROC 0.895). Those positives differ from their negatives in
   the call itself (an unrequested transfer to a recipient the user never named),
   not only in the observation. InjecAgent removes the call-level difference and
   the signal disappears. So the transferable part of "injection detection" in
   v4 is call-level: is this action something the user asked for. Reading the
   untrusted content for an instruction that explains the action is not learned,
   at either size. The v4 generator's leak (`docs/results/notes/injection-label-leak-diagnosis.md`)
   is the likely reason: the training signal was carried by an argument key, so
   the model never needed the observation.

3. **Policy checking transfers again.** `policy_conflict` 0.965 (2B) and 0.977
   (8B) against a 0.464 base rate on five policies written for this port, over
   38 toolkits the checker never saw. The rule baseline is at base rate. Stripping
   identity barely moves it here (0.977 to 0.968) because the five policies are
   global rules about the call, not about who the principal is, unlike the
   AgentDojo banking policies which reference what the user named.

4. **`unauthorized_scope` has signal at 8B here, not at 2B.** 0.849 / 0.691
   against 0.752 base rate for 8B; 2B at base rate. The label is clean on this
   dataset (attacker tool vs user tool), so this is a real but modest size effect.

5. **What v6 had to show, and did.** The v6 checkers, trained without the leak
   on long multi-format observations with the instruction at random positions,
   are the test of whether the observation channel can be learned at all. The
   paired poisoned-vs-clean fraction is the metric; 0.5 is chance; v6 is at
   0.977 at both sizes (reading 0). `unauthorized_scope` for v6 (0.704 2B,
   0.677 8B) is below the 0.752 base rate; the 8B v4 signal on it (0.849) did
   not survive the retrain. Stripping identity at eval time from 8B v6 raises
   it to 0.917 / 0.786: the port fills principal and delegated-scope fields
   with placeholders, and the v6 head reads them as authorising the attacker
   call. Stripping leaves injection (0.953 / 0.949, pair win 0.978, median raw
   +3.25 vs -4.00) and policy (0.963) unchanged, so the v6 injection signal is
   carried by the observation text, not by identity fields.

6. **Baselines.** Granite Guardian is at chance on injection (0.537 AUROC) and
   below base rate elsewhere. The same Granite-3.3-8B base asked ALLOW/STOP as
   the agent is also at chance on injection (0.597) but flags every attacker
   call as STOP (`unauthorized_scope` 1.000): the untrained agent recognises
   that the attacker tool is unrelated to the user's request, which is the same
   call-level judgement the v4 checkers make; only the v6 checkers read the
   poisoned text.
   Baseline rows are on a fixed 1,000-row subsample (injection n=767, positive
   rates 0.471 / 0.767 / 0.466 / 0.048 / 0.154).

Reports: `rule-baseline-report.md`, `decoder-2b-v4-report.md`,
`decoder-8b-v4-report.md`, `decoder-8b-v4-strip-report.md`, `decoder-2b-v6-report.md`, `decoder-8b-v6-report.md`, `decoder-8b-v6-strip-report.md`, `guardian-3.3-8b-report.md`, `agent-self-8b-report.md` (ECE column is raw
margins, no calibration bundle applies when identity is stripped at eval time).
Score dumps are on FSx under `runs/<run>/reports/injecagent/scores.jsonl`.
