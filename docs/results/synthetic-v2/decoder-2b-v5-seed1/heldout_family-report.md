# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6692, sha256=c35eda561f89afd8165d706b1a3ef4e851b100cf8ef9239bde1ea633372c6cd7
Seed: 0. Generated at: 2026-09-22T16:39:35.824213+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6692 | 0.0813 | 0.8595 | 1.0000 | 1.0000 | 0.7482 | 0.8559 | 0.7873 | 0.8948 | 0.0041 |
| unauthorized_scope | 6393 | 0.1215 | 1.0000 | 0.9975 | 1.0000 | 0.9974 | 0.9987 | 1.0000 | 1.0000 | 0.0000 |
| sensitive_data_exposure | 1521 | 0.2078 | 1.0000 | 0.9991 | 1.0000 | 0.9968 | 0.9984 | 1.0000 | 1.0000 | 0.0001 |
| untrusted_destination | 2102 | 0.3601 | 0.9980 | 0.8698 | 0.9974 | 1.0000 | 0.9987 | 1.0000 | 1.0000 | 0.0011 |
| privilege_escalation | 6692 | 0.0693 | 1.0000 | 0.9999 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 6692 | 0.0867 | 0.9842 | 0.9848 | 1.0000 | 0.9690 | 0.9842 | 0.9943 | 0.9994 | 0.0012 |
| financial_commitment | 6692 | 0.0865 | 1.0000 | 0.9998 | 1.0000 | 0.9965 | 0.9983 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 279 | 0.5054 | 0.9964 | 0.9985 | 1.0000 | 0.9362 | 0.9670 | 1.0000 | 1.0000 | 0.0034 |
| policy_conflict | 1894 | 0.3025 | 0.8756 | 0.2451 | 0.8772 | 0.8726 | 0.8749 | 0.9477 | 0.9740 | 0.0420 |
| suspicious_action_sequence | 1324 | 0.2938 | 0.9194 | 0.6140 | 1.0000 | 0.8509 | 0.9194 | 0.9546 | 0.9769 | 0.0095 |
| insufficient_context | 6692 | 0.0837 | 0.8214 | 0.7042 | 0.9974 | 0.6946 | 0.8189 | 0.8061 | 0.9055 | 0.0074 |

## Macro / worst slice

- macro `precision` = 0.9902
- macro `recall` = 0.9198
- macro `f1` = 0.9504
- macro `f1@selected` = 0.9468
- macro `auprc` = 0.9536
- macro `auroc` = 0.9773
- macro `brier` = 0.0132
- macro `ece` = 0.0062
- worst-slice `precision` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.4091 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.4242 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8182 (contrastive_axis=environment_stage)
- worst-slice `auroc` = 0.8200 (contrastive_axis=environment_stage)
- worst-slice `brier` = 0.0002 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0056 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: 0.9808 over 104 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9361
- surface-paraphrase invariance (mean |dp|): 0.0036, fraction moved: 0.0909

## Approval elimination

Bundle `balanced`, n=6692, base incident rate=0.5767, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0025 | 0.0000 | 0.6877 | 0.3098 |
| 0.500% | 0.0025 | 0.0000 | 0.6877 | 0.3098 |
| 1.000% | 0.0025 | 0.0000 | 0.6877 | 0.3098 |
| 2.000% | 0.0025 | 0.0000 | 0.6877 | 0.3098 |
| 5.000% | 0.0036 | 0.0417 | 0.6866 | 0.3098 |
