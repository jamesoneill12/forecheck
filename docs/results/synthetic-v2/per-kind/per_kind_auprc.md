### v4 data, 2B v4 (ADR 0010 two-kind withheld set)
withheld kinds: ['data_residency_region', 'forbid_recipient_domain']
rows: 2247; checkers: 2Bv4

| group | 2Bv4 |
|---|---|
| data_residency_region | 0.914 / 0.880 (n=1169, pos=0.61) |
| forbid_recipient_domain | 0.836 / 0.922 (n=1135, pos=0.20) |
| (no withheld kind) | n/a |
| (all rows) | 0.752 / 0.767 (n=2247, pos=0.40) |

Cells: AUPRC / AUROC on policy_conflict raw margin.

### v5 data, 2B v5
withheld kinds: ['forbid_cross_tenant_reference', 'forbid_weekend_ops', 'max_records_per_day_quota', 'require_data_classification_below']
rows: 2321; checkers: 2Bv5

| group | 2Bv5 |
|---|---|
| forbid_cross_tenant_reference | 0.792 / 0.900 (n=574, pos=0.29) |
| forbid_weekend_ops | 0.873 / 0.900 (n=614, pos=0.35) |
| max_records_per_day_quota | 0.823 / 0.744 (n=596, pos=0.55) |
| require_data_classification_below | 0.707 / 0.897 (n=615, pos=0.16) |
| (no withheld kind) | n/a |
| (all rows) | 0.704 / 0.773 (n=2316, pos=0.33) |

Cells: AUPRC / AUROC on policy_conflict raw margin.

### v6 data, 2B v6 and 8B v6
withheld kinds: ['forbid_cross_tenant_reference', 'forbid_weekend_ops', 'max_records_per_day_quota', 'require_data_classification_below']
rows: 2321; checkers: 2Bv6, 8Bv6

| group | 2Bv6 | 8Bv6 |
|---|---|---|
| forbid_cross_tenant_reference | 0.711 / 0.817 (n=574, pos=0.29) | 0.901 / 0.953 (n=574, pos=0.29) |
| forbid_weekend_ops | 0.867 / 0.887 (n=614, pos=0.35) | 0.959 / 0.972 (n=614, pos=0.35) |
| max_records_per_day_quota | 0.819 / 0.737 (n=596, pos=0.55) | 0.756 / 0.675 (n=596, pos=0.55) |
| require_data_classification_below | 0.630 / 0.890 (n=615, pos=0.16) | 0.632 / 0.913 (n=615, pos=0.16) |
| (no withheld kind) | n/a | n/a |
| (all rows) | 0.692 / 0.767 (n=2316, pos=0.33) | 0.767 / 0.869 (n=2316, pos=0.33) |

Cells: AUPRC / AUROC on policy_conflict raw margin.
