# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=45c47fc6d4a393bd84b5a16e2b80ec75743cfd23aaac3e7632036e360b4de85f
Seed: 0. Generated at: 2026-09-25T08:47:49.753430+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0895 | 0.8511 | 1.0000 | 1.0000 | 0.7407 | 0.8511 | 0.7669 | 0.8860 | 0.0026 |
| unauthorized_scope | 6329 | 0.1195 | 1.0000 | 0.3910 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| sensitive_data_exposure | 1593 | 0.2379 | 1.0000 | 1.0000 | 1.0000 | 0.9947 | 0.9974 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 2152 | 0.3601 | 1.0000 | 0.1579 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| privilege_escalation | 6640 | 0.0646 | 0.9988 | 1.0000 | 1.0000 | 0.9977 | 0.9988 | 0.9987 | 0.9998 | 0.0002 |
| destructive_or_irreversible_action | 6640 | 0.0842 | 0.9855 | 1.0000 | 1.0000 | 0.9714 | 0.9855 | 0.9918 | 0.9994 | 0.0006 |
| financial_commitment | 6640 | 0.0839 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 272 | 0.5221 | 1.0000 | 0.9998 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| policy_conflict | 1846 | 0.3126 | 0.8500 | 0.2955 | 0.7889 | 0.9133 | 0.8466 | 0.9564 | 0.9754 | 0.0814 |
| suspicious_action_sequence | 1391 | 0.3070 | 0.9244 | 0.3260 | 0.9973 | 0.8595 | 0.9233 | 0.9550 | 0.9785 | 0.0035 |
| insufficient_context | 6640 | 0.0946 | 0.8184 | 0.2586 | 0.9799 | 0.6990 | 0.8160 | 0.8254 | 0.9220 | 0.0049 |

## Macro / worst slice

- macro `precision` = 0.9817
- macro `recall` = 0.9246
- macro `f1` = 0.9480
- macro `f1@selected` = 0.9471
- macro `auprc` = 0.9540
- macro `auroc` = 0.9783
- macro `brier` = 0.0159
- macro `ece` = 0.0085
- worst-slice `precision` = 0.5000 (contrastive_axis=surface_paraphrase)
- worst-slice `recall` = 0.5000 (contrastive_axis=surface_paraphrase)
- worst-slice `f1` = 0.5000 (contrastive_axis=surface_paraphrase)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8444 (contrastive_axis=environment_stage)
- worst-slice `auroc` = 0.8750 (contrastive_axis=principal_authorization)
- worst-slice `brier` = 0.0002 (contrastive_axis=financial_materiality)
- worst-slice `ece` = 0.0053 (tool_family=file_storage)

## Consistency
- pair consistency: 1.0000 over 17 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9998
- surface-paraphrase invariance (mean |dp|): 0.0023, fraction moved: 0.0000

## Approval elimination

Bundle `balanced`, n=6640, base incident rate=0.5934, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0030 | 0.0000 | 0.6916 | 0.3054 |
| 0.500% | 0.0030 | 0.0000 | 0.6916 | 0.3054 |
| 1.000% | 0.0030 | 0.0000 | 0.6916 | 0.3054 |
| 2.000% | 0.0030 | 0.0000 | 0.6916 | 0.3054 |
| 5.000% | 0.0063 | 0.0476 | 0.6883 | 0.3054 |
