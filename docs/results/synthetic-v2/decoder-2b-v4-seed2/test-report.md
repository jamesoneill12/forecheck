# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T15:31:01.296641+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8609 | 0.9999 | 1.0000 | 0.7558 | 0.8609 | 0.7990 | 0.9044 | 0.0002 |
| unauthorized_scope | 4216 | 0.1191 | 0.9980 | 0.0016 | 1.0000 | 0.9980 | 0.9990 | 1.0000 | 1.0000 | 0.0005 |
| sensitive_data_exposure | 1073 | 0.2144 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 1367 | 0.3555 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| privilege_escalation | 4412 | 0.0161 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9808 | 0.9987 | 1.0000 | 0.9584 | 0.9788 | 0.9944 | 0.9994 | 0.0019 |
| financial_commitment | 4412 | 0.0780 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 95 | 0.5368 | 1.0000 | 0.9985 | 1.0000 | 0.9804 | 0.9901 | 1.0000 | 1.0000 | 0.0001 |
| policy_conflict | 752 | 0.3590 | 0.9697 | 0.3938 | 0.9701 | 0.9630 | 0.9665 | 0.9952 | 0.9971 | 0.0112 |
| suspicious_action_sequence | 904 | 0.3208 | 0.9568 | 0.2072 | 0.9709 | 0.9207 | 0.9451 | 0.9773 | 0.9875 | 0.0064 |
| insufficient_context | 4412 | 0.0857 | 0.7765 | 0.8254 | 0.9839 | 0.6455 | 0.7796 | 0.7939 | 0.9044 | 0.0062 |

## Macro / worst slice

- macro `precision` = 0.9964
- macro `recall` = 0.9298
- macro `f1` = 0.9584
- macro `f1@selected` = 0.9564
- macro `auprc` = 0.9600
- macro `auroc` = 0.9812
- macro `brier` = 0.0085
- macro `ece` = 0.0024
- worst-slice `precision` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8091 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.8958 (contrastive_axis=policy_present_versus_absent)
- worst-slice `brier` = 0.0002 (contrastive_axis=surface_paraphrase)
- worst-slice `ece` = 0.0024 (split=test)

## Consistency
- pair consistency: 0.9811 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9689
- surface-paraphrase invariance (mean |dp|): 0.0102, fraction moved: 0.3478

## Approval elimination

Bundle `balanced`, n=4412, base incident rate=0.5585, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0095 | 0.0000 | 0.6469 | 0.3436 |
| 0.500% | 0.0095 | 0.0000 | 0.6469 | 0.3436 |
| 1.000% | 0.0095 | 0.0000 | 0.6469 | 0.3436 |
| 2.000% | 0.0147 | 0.0154 | 0.6417 | 0.3436 |
| 5.000% | 0.2550 | 0.0498 | 0.4014 | 0.3436 |
