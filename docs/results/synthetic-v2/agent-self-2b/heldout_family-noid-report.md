# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=2000, sha256=ac0b60d6b5ca926accf6672beb60c33abbbdabd73d57ef8d71ba3f7ee2ee165e
Seed: 0. Generated at: 2026-09-22T10:42:06.070829+00:00.
Model: agent_self/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0750 | 0.2222 | n/a | n/a | n/a | n/a | 0.1854 | 0.7223 | 0.3399 |
| unauthorized_scope | 1909 | 0.1058 | 0.1468 | n/a | n/a | n/a | n/a | 0.1007 | 0.4794 | 0.3400 |
| sensitive_data_exposure | 476 | 0.2143 | 0.2960 | n/a | n/a | n/a | n/a | 0.2326 | 0.5345 | 0.2781 |
| untrusted_destination | 650 | 0.3554 | 0.3880 | n/a | n/a | n/a | n/a | 0.3682 | 0.5004 | 0.2991 |
| privilege_escalation | 2000 | 0.0745 | 0.1326 | n/a | n/a | n/a | n/a | 0.0769 | 0.5328 | 0.3404 |
| destructive_or_irreversible_action | 2000 | 0.0855 | 0.1689 | n/a | n/a | n/a | n/a | 0.0959 | 0.5403 | 0.3437 |
| financial_commitment | 2000 | 0.1005 | 0.1507 | n/a | n/a | n/a | n/a | 0.1041 | 0.5277 | 0.3247 |
| external_communication | 84 | 0.5357 | 0.6042 | n/a | n/a | n/a | n/a | 0.5667 | 0.5436 | 0.2137 |
| policy_conflict | 556 | 0.3849 | 0.3981 | n/a | n/a | n/a | n/a | 0.4169 | 0.5490 | 0.2472 |
| suspicious_action_sequence | 435 | 0.3057 | 0.3295 | n/a | n/a | n/a | n/a | 0.2621 | 0.4106 | 0.3759 |
| insufficient_context | 2000 | 0.0790 | 0.1313 | n/a | n/a | n/a | n/a | 0.0818 | 0.4944 | 0.3552 |

## Macro / worst slice

- macro `precision` = 0.2208
- macro `recall` = 0.4409
- macro `f1` = 0.2698
- macro `f1@selected` = n/a
- macro `auprc` = 0.2265
- macro `auroc` = 0.5305
- macro `brier` = 0.3099
- macro `ece` = 0.3144
- worst-slice `precision` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.1830 (difficulty=hard)
- worst-slice `auroc` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `brier` = 0.1921 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `ece` = 0.2677 (trajectory_length=1-3)

## Consistency
- pair consistency: 0.7222 over 18 directional pairs
- counterfactual sensitivity (mean |dp|): 0.2375
- surface-paraphrase invariance (mean |dp|): 0.5156, fraction moved: 1.0000

## Self-judgment vs external checker

The agent produces one ALLOW/STOP decision per example, not per dimension; the same score is evaluated against every dimension's labels below, so this measures how well a single act/refuse decision happens to cover each dimension -- not eleven independent judgments.

| dimension | agent auprc | agent recall@selected |
|---|---|---|
| prompt_injection_influence | 0.1854 | n/a |
| unauthorized_scope | 0.1007 | n/a |
| sensitive_data_exposure | 0.2326 | n/a |
| untrusted_destination | 0.3682 | n/a |
| privilege_escalation | 0.0769 | n/a |
| destructive_or_irreversible_action | 0.0959 | n/a |
| financial_commitment | 0.1041 | n/a |
| external_communication | 0.5667 | n/a |
| policy_conflict | 0.4169 | n/a |
| suspicious_action_sequence | 0.2621 | n/a |
| insufficient_context | 0.0818 | n/a |
