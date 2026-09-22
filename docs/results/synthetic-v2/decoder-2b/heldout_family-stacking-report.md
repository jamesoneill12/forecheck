# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T23:19:10.807902+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8727 | 0.9999 | 1.0000 | 0.7652 | 0.8670 | 0.8098 | 0.9080 | 0.0019 |
| unauthorized_scope | 6315 | 0.1123 | 1.0000 | 0.9981 | 1.0000 | 0.9944 | 0.9972 | 1.0000 | 1.0000 | 0.0000 |
| sensitive_data_exposure | 1540 | 0.2143 | 1.0000 | 0.9997 | 1.0000 | 0.9970 | 0.9985 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 2109 | 0.3580 | 0.9980 | 0.9865 | 0.9987 | 0.9987 | 0.9987 | 0.9999 | 1.0000 | 0.0016 |
| privilege_escalation | 6640 | 0.0637 | 0.4642 | 0.2344 | 0.4029 | 0.7801 | 0.5314 | 0.4598 | 0.9491 | 0.0161 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.9840 | 0.9994 | 1.0000 | 0.9684 | 0.9840 | 0.9928 | 0.9993 | 0.0005 |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 0.9993 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 284 | 0.5775 | 1.0000 | 0.9997 | 1.0000 | 0.9878 | 0.9939 | 1.0000 | 1.0000 | 0.0004 |
| policy_conflict | 1891 | 0.3178 | 0.9805 | 0.9852 | 1.0000 | 0.9534 | 0.9761 | 0.9985 | 0.9996 | 0.0050 |
| suspicious_action_sequence | 1289 | 0.3313 | 0.9149 | 0.3309 | 0.9972 | 0.8454 | 0.9151 | 0.9524 | 0.9700 | 0.0093 |
| insufficient_context | 6640 | 0.0861 | 0.8483 | 0.3241 | 0.9491 | 0.7500 | 0.8379 | 0.8487 | 0.9347 | 0.0070 |

## Macro / worst slice

- macro `precision` = 0.9557
- macro `recall` = 0.8822
- macro `f1` = 0.9148
- macro `f1@selected` = 0.9182
- macro `auprc` = 0.9147
- macro `auroc` = 0.9782
- macro `brier` = 0.0124
- macro `ece` = 0.0038
- worst-slice `precision` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8463 (contrastive_axis=permission_versus_escalation)
- worst-slice `auroc` = 0.9304 (policy_absent)
- worst-slice `brier` = 0.0008 (contrastive_axis=financial_materiality)
- worst-slice `ece` = 0.0026 (tool_family=production_ops)

## Consistency
- pair consistency: 0.9811 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9065
- surface-paraphrase invariance (mean |dp|): 0.0034, fraction moved: 0.0909

## Multi-policy stacking

Independent = OR across the first k policies evaluated separately (each guard alone decides, the stack takes the most severe). Joint = the first k policies' rules merged into one bundle and evaluated once by the forecheck policy engine, in threshold mode. expected_cost_joint = the same merged bundle evaluated in decision_mode: expected_cost, using the joint probability vector instead of per-rule thresholds.

| k | strategy | policies | n | benign_covered | risky_covered | fpr | fnr | review_rate | mean_cost |
|---|---|---|---|---|---|---|---|---|---|
| 1 | independent | permissive | 6640 | 3785 | 2855 | 0.0145 | 0.2532 | 0.3069 | 1.0382 |
| 1 | joint | permissive | 6640 | 3785 | 2855 | 0.0145 | 0.2532 | 0.3069 | 1.0382 |
| 1 | expected_cost_joint | permissive | 6640 | 3785 | 2855 | 0.0576 | 0.1699 | 0.3673 | 0.8052 |
| 2 | independent | permissive, balanced | 6640 | 2790 | 3850 | 0.1398 | 0.0797 | 0.2962 | 0.1939 |
| 2 | joint | permissive, balanced | 6640 | 2790 | 3850 | 0.1308 | 0.1052 | 0.2777 | 0.2557 |
| 2 | expected_cost_joint | permissive, balanced | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 3 | independent | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.9663 | 0.0161 | 0.6581 | 0.2017 |
| 3 | joint | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.6340 | 0.2904 |
| 3 | expected_cost_joint | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 4 | independent | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.9663 | 0.0109 | 0.6611 | 0.1759 |
| 4 | joint | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.6340 | 0.2904 |
| 4 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 5 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.9663 | 0.0109 | 0.6422 | 0.1723 |
| 5 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.6170 | 0.2871 |
| 5 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 6 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.9663 | 0.0109 | 0.6422 | 0.1723 |
| 6 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.6170 | 0.2871 |
| 6 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 7 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.9663 | 0.0109 | 0.6280 | 0.1703 |
| 7 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.6048 | 0.2854 |
| 7 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 8 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.9663 | 0.0065 | 0.5794 | 0.1392 |
| 8 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.5584 | 0.2802 |
| 8 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 9 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.9663 | 0.0065 | 0.5143 | 0.1297 |
| 9 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.4843 | 0.2695 |
| 9 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 10 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.9663 | 0.0065 | 0.4643 | 0.1227 |
| 10 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.4386 | 0.2633 |
| 10 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 11 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.9663 | 0.0065 | 0.4419 | 0.1194 |
| 11 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.4149 | 0.2599 |
| 11 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 12 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.9667 | 0.0065 | 0.4330 | 0.1182 |
| 12 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.4065 | 0.2589 |
| 12 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 13 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.9667 | 0.0031 | 0.4017 | 0.1136 |
| 13 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.3764 | 0.2543 |
| 13 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 14 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.9667 | 0.0031 | 0.4017 | 0.1136 |
| 14 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.3764 | 0.2543 |
| 14 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
| 15 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.9667 | 0.0031 | 0.4017 | 0.1136 |
| 15 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.9047 | 0.0514 | 0.3764 | 0.2543 |
| 15 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.0817 | 0.0696 | 0.2777 | 0.1247 |
