# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T23:22:03.263851+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8124 | 0.9928 | 0.9977 | 0.7742 | 0.8718 | 0.8171 | 0.8820 | 0.0274 |
| unauthorized_scope | 6315 | 0.1123 | 0.9922 | 0.9349 | 0.9956 | 0.9647 | 0.9799 | 0.9992 | 0.9999 | 0.0017 |
| sensitive_data_exposure | 1540 | 0.2143 | 0.9865 | 0.6785 | 0.9880 | 0.9939 | 0.9909 | 0.9995 | 0.9999 | 0.0046 |
| untrusted_destination | 2109 | 0.3580 | 0.9967 | 0.2476 | 1.0000 | 0.9934 | 0.9967 | 0.9983 | 0.9986 | 0.0100 |
| privilege_escalation | 6640 | 0.0637 | 0.4836 | 0.8665 | 0.0000 | 0.0000 | 0.0000 | 0.4807 | 0.9377 | 0.0100 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.8874 | 0.9686 | 0.9732 | 0.9668 | 0.9700 | 0.9861 | 0.9978 | 0.0234 |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 0.9060 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0022 |
| external_communication | 284 | 0.5775 | 0.9939 | 0.7287 | 1.0000 | 0.9817 | 0.9908 | 1.0000 | 0.9999 | 0.0302 |
| policy_conflict | 1891 | 0.3178 | 0.4632 | 0.4435 | 0.3406 | 0.9101 | 0.4957 | 0.4168 | 0.5984 | 0.1887 |
| suspicious_action_sequence | 1289 | 0.3313 | 0.7298 | 0.6604 | 0.8010 | 0.7166 | 0.7565 | 0.8691 | 0.8970 | 0.0974 |
| insufficient_context | 6640 | 0.0861 | 0.5963 | 0.8142 | 0.5908 | 0.7168 | 0.6477 | 0.6792 | 0.9166 | 0.1444 |

## Macro / worst slice

- macro `precision` = 0.7892
- macro `recall` = 0.8552
- macro `f1` = 0.8129
- macro `f1@selected` = 0.7909
- macro `auprc` = 0.8405
- macro `auroc` = 0.9298
- macro `brier` = 0.0507
- macro `ece` = 0.0491
- worst-slice `precision` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.3939 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7697 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.7500 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0297 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0378 (policy_absent)

## Consistency
- pair consistency: 0.9811 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8808
- surface-paraphrase invariance (mean |dp|): 0.0370, fraction moved: 0.9091

## Multi-policy stacking

Independent = OR across the first k policies evaluated separately (each guard alone decides, the stack takes the most severe). Joint = the first k policies' rules merged into one bundle and evaluated once by the forecheck policy engine, in threshold mode. expected_cost_joint = the same merged bundle evaluated in decision_mode: expected_cost, using the joint probability vector instead of per-rule thresholds.

| k | strategy | policies | n | benign_covered | risky_covered | fpr | fnr | review_rate | mean_cost |
|---|---|---|---|---|---|---|---|---|---|
| 1 | independent | permissive | 6640 | 3785 | 2855 | 0.3456 | 0.1632 | 0.5276 | 0.7900 |
| 1 | joint | permissive | 6640 | 3785 | 2855 | 0.3456 | 0.1632 | 0.5276 | 0.7900 |
| 1 | expected_cost_joint | permissive | 6640 | 3785 | 2855 | 0.5886 | 0.0504 | 0.7146 | 0.4491 |
| 2 | independent | permissive, balanced | 6640 | 2790 | 3850 | 0.7097 | 0.0421 | 0.2583 | 0.1586 |
| 2 | joint | permissive, balanced | 6640 | 2790 | 3850 | 0.6968 | 0.0564 | 0.2446 | 0.2016 |
| 2 | expected_cost_joint | permissive, balanced | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 3 | independent | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.9900 | 0.0075 | 0.2062 | 0.1170 |
| 3 | joint | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.3652 | 0.2239 |
| 3 | expected_cost_joint | permissive, balanced, conservative | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 4 | independent | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.9903 | 0.0049 | 0.2078 | 0.1003 |
| 4 | joint | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.3652 | 0.2239 |
| 4 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 5 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.9903 | 0.0049 | 0.2008 | 0.0989 |
| 5 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.3547 | 0.2218 |
| 5 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 6 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.9903 | 0.0049 | 0.2008 | 0.0989 |
| 6 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.3547 | 0.2218 |
| 6 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 7 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.9903 | 0.0049 | 0.1968 | 0.0984 |
| 7 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.3452 | 0.2207 |
| 7 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 8 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.9939 | 0.0018 | 0.0639 | 0.0650 |
| 8 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.1111 | 0.1885 |
| 8 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 9 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.9939 | 0.0018 | 0.0639 | 0.0650 |
| 9 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.1111 | 0.1885 |
| 9 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 10 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.9939 | 0.0018 | 0.0548 | 0.0647 |
| 10 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0992 | 0.1878 |
| 10 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 11 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.9939 | 0.0018 | 0.0529 | 0.0643 |
| 11 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0949 | 0.1869 |
| 11 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 12 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.9953 | 0.0016 | 0.0489 | 0.0640 |
| 12 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0833 | 0.1852 |
| 12 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 13 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.9986 | 0.0000 | 0.0051 | 0.0575 |
| 13 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0170 | 0.1752 |
| 13 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 14 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.9986 | 0.0000 | 0.0051 | 0.0575 |
| 14 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0145 | 0.1747 |
| 14 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
| 15 | independent | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.9986 | 0.0000 | 0.0051 | 0.0575 |
| 15 | joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.9491 | 0.0312 | 0.0145 | 0.1747 |
| 15 | expected_cost_joint | permissive, balanced, conservative, expected-cost-example, synthetic-prompt_injection_influence, synthetic-unauthorized_scope, synthetic-sensitive_data_exposure, synthetic-untrusted_destination, synthetic-privilege_escalation, synthetic-destructive_or_irreversible_action, synthetic-financial_commitment, synthetic-external_communication, synthetic-policy_conflict, synthetic-suspicious_action_sequence, synthetic-insufficient_context | 6640 | 2790 | 3850 | 0.9208 | 0.0101 | 0.3655 | 0.1065 |
