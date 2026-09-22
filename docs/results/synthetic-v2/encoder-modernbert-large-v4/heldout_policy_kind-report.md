# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2247, sha256=99c768cce2dd5ac344288cf1ca35a2825ca52a9ea3002ff39d94f71c96406a2c
Seed: 0. Generated at: 2026-09-22T13:13:57.539986+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2247 | 0.0757 | 0.8166 | 0.9767 | 1.0000 | 0.6941 | 0.8194 | 0.7448 | 0.8582 | 0.0075 |
| unauthorized_scope | 2139 | 0.1169 | 0.9208 | 0.8287 | 0.9625 | 0.9240 | 0.9429 | 0.9857 | 0.9979 | 0.0184 |
| sensitive_data_exposure | 510 | 0.2118 | 0.7127 | 0.6654 | 0.7257 | 0.7593 | 0.7421 | 0.8419 | 0.9454 | 0.1291 |
| untrusted_destination | 647 | 0.3215 | 0.9624 | 0.2933 | 0.8966 | 1.0000 | 0.9455 | 0.9979 | 0.9990 | 0.0230 |
| privilege_escalation | 2247 | 0.0191 | 0.9556 | 0.9986 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0016 |
| destructive_or_irreversible_action | 2247 | 0.0961 | 0.9814 | 0.7266 | 0.9906 | 0.9769 | 0.9837 | 0.9968 | 0.9996 | 0.0027 |
| financial_commitment | 2247 | 0.0797 | 1.0000 | 0.9171 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| external_communication | 53 | 0.6226 | 0.7368 | 0.2869 | 0.7045 | 0.9394 | 0.8052 | 0.9139 | 0.8394 | 0.0970 |
| policy_conflict | 2247 | 0.4050 | 0.5234 | 0.4680 | 0.4332 | 0.8451 | 0.5728 | 0.4458 | 0.5601 | 0.1094 |
| suspicious_action_sequence | 460 | 0.3130 | 0.5668 | 0.4024 | 0.4744 | 0.7708 | 0.5873 | 0.5486 | 0.7414 | 0.1237 |
| insufficient_context | 2247 | 0.0788 | 0.6526 | 0.6635 | 0.5720 | 0.8079 | 0.6698 | 0.7339 | 0.9615 | 0.0981 |

## Macro / worst slice

- macro `precision` = 0.7873
- macro `recall` = 0.8456
- macro `f1` = 0.8026
- macro `f1@selected` = 0.8244
- macro `auprc` = 0.8372
- macro `auroc` = 0.9002
- macro `brier` = 0.0760
- macro `ece` = 0.0555
- worst-slice `precision` = 0.0741 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.0889 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6252 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.4375 (contrastive_axis=permission_versus_escalation)
- worst-slice `brier` = 0.0353 (contrastive_axis=surface_paraphrase)
- worst-slice `ece` = 0.0489 (tool_family=database_warehouse)

## Consistency
- pair consistency: 1.0000 over 31 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8534
- surface-paraphrase invariance (mean |dp|): 0.0354, fraction moved: 0.8000
