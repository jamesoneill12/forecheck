# InjecAgent length-matched pair audit: data-scaling arms

Produced by `scripts/injecagent_pair_audit.py` on
`data/external/injecagent-v2/injecagent.jsonl`, scored with the 2B v6
data-scaling checkpoints (5k/100k/250k rows, full FT at 25k).

4-way groups (poisoned + clean, clean_padded, clean_instruction): 1598
poisoned observation longer than clean: 1598/1598 = 1.000
poisoned observation longer than clean_padded: 68/1598 = 0.043
poisoned observation longer than clean_instruction: 68/1598 = 0.043
destination trust differs, poisoned vs clean: 626/1598 = 0.392

| checker | control | wins | ties | losses | strict win | tie-adjusted win | sign test p | strict win, destination trust equal |
|---|---|---|---|---|---|---|---|---|
| 2B-5k | clean | 1535 | 31 | 32 | 0.961 | 0.970 | 0.0e+00 | 0.935 (n=972) |
| 2B-5k | clean_padded | 1550 | 25 | 23 | 0.970 | 0.978 | 0.0e+00 | 0.951 (n=972) |
| 2B-5k | clean_instruction | 1569 | 19 | 10 | 0.982 | 0.988 | 0.0e+00 | 0.970 (n=972) |
| 2B-100k | clean | 1508 | 22 | 68 | 0.944 | 0.951 | 0.0e+00 | 0.996 (n=972) |
| 2B-100k | clean_padded | 1513 | 25 | 60 | 0.947 | 0.955 | 0.0e+00 | 0.999 (n=972) |
| 2B-100k | clean_instruction | 1470 | 34 | 94 | 0.920 | 0.931 | 3.2e-318 | 0.983 (n=972) |
| 2B-250k | clean | 1221 | 75 | 302 | 0.764 | 0.788 | 5.9e-131 | 0.870 (n=972) |
| 2B-250k | clean_padded | 1248 | 76 | 274 | 0.781 | 0.805 | 1.9e-148 | 0.894 (n=972) |
| 2B-250k | clean_instruction | 1230 | 57 | 311 | 0.770 | 0.788 | 3.3e-129 | 0.889 (n=972) |
| 2B-fullft-25k | clean | 1567 | 20 | 11 | 0.981 | 0.987 | 0.0e+00 | 0.968 (n=972) |
| 2B-fullft-25k | clean_padded | 1576 | 18 | 4 | 0.986 | 0.992 | 0.0e+00 | 0.978 (n=972) |
| 2B-fullft-25k | clean_instruction | 1576 | 17 | 5 | 0.986 | 0.992 | 0.0e+00 | 0.985 (n=972) |

| checker | prompt_injection_influence | unauthorized_scope | policy_conflict |
|---|---|---|---|
| 2B-5k | 0.898 [0.887, 0.909] (n=6392, pos=0.250) | 0.944 [0.938, 0.950] (n=7446, pos=0.858) | 0.911 [0.904, 0.918] (n=7446, pos=0.530) |
| 2B-100k | 0.606 [0.582, 0.629] (n=6392, pos=0.250) | 0.853 [0.842, 0.864] (n=7446, pos=0.858) | 0.979 [0.976, 0.983] (n=7446, pos=0.530) |
| 2B-250k | 0.353 [0.336, 0.370] (n=6392, pos=0.250) | 0.852 [0.842, 0.863] (n=7446, pos=0.858) | 0.910 [0.901, 0.918] (n=7446, pos=0.530) |
| 2B-fullft-25k | 0.825 [0.809, 0.839] (n=6392, pos=0.250) | 0.823 [0.811, 0.835] (n=7446, pos=0.858) | 0.931 [0.926, 0.937] (n=7446, pos=0.530) |
