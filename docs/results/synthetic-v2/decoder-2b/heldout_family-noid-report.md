# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T22:49:24.267874+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8727 | 9.2500 | 1.0000 | 0.7652 | 0.8670 | 0.8102 | 0.9019 | n/a |
| unauthorized_scope | 6315 | 0.1123 | 0.1971 | 0.5000 | 0.1108 | 0.8886 | 0.1971 | 0.1155 | 0.4983 | 0.1283 |
| sensitive_data_exposure | 1540 | 0.2143 | 1.0000 | 8.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | n/a |
| untrusted_destination | 2109 | 0.3580 | 0.9980 | 6.5000 | 0.9974 | 1.0000 | 0.9987 | 0.9960 | 0.9992 | n/a |
| privilege_escalation | 6640 | 0.0637 | 0.0000 | -0.8750 | 0.4076 | 0.7612 | 0.5309 | 0.4682 | 0.9567 | 0.0278 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.9840 | 8.0000 | 1.0000 | 0.9684 | 0.9840 | 0.9930 | 0.9993 | n/a |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 7.2500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | n/a |
| external_communication | 284 | 0.5775 | 1.0000 | 8.2500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | n/a |
| policy_conflict | 1891 | 0.3178 | 0.0000 | -6.2500 | 0.3175 | 0.9983 | 0.4817 | 0.3445 | 0.5397 | n/a |
| suspicious_action_sequence | 1289 | 0.3313 | 0.9149 | 0.0000 | 1.0000 | 0.8478 | 0.9176 | 0.9504 | 0.9699 | 0.0016 |
| insufficient_context | 6640 | 0.0861 | 0.4875 | -1.7500 | 0.9788 | 0.3234 | 0.4862 | 0.4184 | 0.6938 | 0.0003 |

## Macro / worst slice

- macro `precision` = 0.7360
- macro `recall` = 0.7089
- macro `f1` = 0.6777
- macro `f1@selected` = 0.7694
- macro `auprc` = 0.7360
- macro `auroc` = 0.8690
- macro `brier` = 103.0951
- macro `ece` = 0.0395
- worst-slice `precision` = 0.2909 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.3636 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.3030 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6447 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.7000 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 81.5935 (tool_family=file_storage)
- worst-slice `ece` = 0.0227 (contrastive_axis=surface_paraphrase)

## Consistency
- pair consistency: 0.8396 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 17.1797
- surface-paraphrase invariance (mean |dp|): 0.3295, fraction moved: 1.0000
