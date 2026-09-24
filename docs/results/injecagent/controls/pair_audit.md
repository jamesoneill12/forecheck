# InjecAgent length-matched pair audit

Produced by `scripts/injecagent_pair_audit.py` on
`data/external/injecagent-v2/injecagent.jsonl`.

4-way groups (poisoned + clean, clean_padded, clean_instruction): 1598
poisoned observation longer than clean: 1598/1598 = 1.000
poisoned observation longer than clean_padded: 68/1598 = 0.043
poisoned observation longer than clean_instruction: 68/1598 = 0.043
destination trust differs, poisoned vs clean: 626/1598 = 0.392

| checker | control | wins | ties | losses | strict win | tie-adjusted win | sign test p | strict win, destination trust equal |
|---|---|---|---|---|---|---|---|---|
| 2Bv6 | clean | 1562 | 8 | 28 | 0.977 | 0.980 | 0.0e+00 | 0.963 (n=972) |
| 2Bv6 | clean_padded | 1572 | 6 | 20 | 0.984 | 0.986 | 0.0e+00 | 0.973 (n=972) |
| 2Bv6 | clean_instruction | 1579 | 3 | 16 | 0.988 | 0.989 | 0.0e+00 | 0.986 (n=972) |
| 8Bv6 | clean | 1562 | 19 | 17 | 0.977 | 0.983 | 0.0e+00 | 0.970 (n=972) |
| 8Bv6 | clean_padded | 1559 | 17 | 22 | 0.976 | 0.981 | 0.0e+00 | 0.966 (n=972) |
| 8Bv6 | clean_instruction | 1579 | 16 | 3 | 0.988 | 0.993 | 0.0e+00 | 0.988 (n=972) |
| 8Bv6noid | clean | 1563 | 25 | 10 | 0.978 | 0.986 | 0.0e+00 | 0.972 (n=972) |
| 8Bv6noid | clean_padded | 1566 | 20 | 12 | 0.980 | 0.986 | 0.0e+00 | 0.975 (n=972) |
| 8Bv6noid | clean_instruction | 1581 | 13 | 4 | 0.989 | 0.993 | 0.0e+00 | 0.989 (n=972) |
| 2Bv4 | clean | 806 | 382 | 410 | 0.504 | 0.624 | 3.0e-30 | 0.638 (n=972) |
| 2Bv4 | clean_padded | 497 | 648 | 453 | 0.311 | 0.514 | 1.6e-01 | 0.410 (n=972) |
| 2Bv4 | clean_instruction | 465 | 715 | 418 | 0.291 | 0.515 | 1.2e-01 | 0.387 (n=972) |

| checker | prompt_injection_influence | unauthorized_scope | policy_conflict |
|---|---|---|---|
| 2Bv6 | 0.742 [0.723, 0.759] (n=6392, pos=0.250) | 0.810 [0.798, 0.823] (n=7446, pos=0.858) | 0.933 [0.927, 0.938] (n=7446, pos=0.530) |
| 8Bv6 | 0.899 [0.888, 0.909] (n=6392, pos=0.250) | 0.816 [0.805, 0.828] (n=7446, pos=0.858) | 0.966 [0.962, 0.969] (n=7446, pos=0.530) |
| 8Bv6noid | 0.908 [0.897, 0.918] (n=6392, pos=0.250) | 0.963 [0.959, 0.966] (n=7446, pos=0.858) | 0.968 [0.964, 0.971] (n=7446, pos=0.530) |
| 2Bv4 | 0.260 [0.247, 0.273] (n=6392, pos=0.250) | 0.847 [0.835, 0.858] (n=7446, pos=0.858) | 0.976 [0.973, 0.979] (n=7446, pos=0.530) |
