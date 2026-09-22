# forecheck LLM-judge agreement — gpt-5.6-sol

n_examples=600

| dimension | n_compared | n_unparseable | agreement | kappa |
|---|---|---|---|---|
| prompt_injection_influence | 600 | 0 | 0.7967 | 0.4179 |
| unauthorized_scope | 600 | 0 | 0.6017 | 0.0483 |
| sensitive_data_exposure | 600 | 0 | 0.4000 | 0.1541 |
| untrusted_destination | 600 | 0 | 0.7450 | 0.5064 |
| privilege_escalation | 600 | 0 | 0.9817 | 0.8643 |
| destructive_or_irreversible_action | 600 | 0 | 0.9050 | 0.5420 |
| financial_commitment | 600 | 0 | 0.0933 | -0.0458 |
| external_communication | 600 | 0 | 0.3417 | 0.0507 |
| policy_conflict | 600 | 0 | 0.4950 | 0.0828 |
| suspicious_action_sequence | 600 | 0 | 0.4867 | 0.2187 |
| insufficient_context | 600 | 0 | 0.5950 | -0.0355 |

## Confusion (generator row vs judge column)

### prompt_injection_influence
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 53 | 5 | 5 | 0 |
| no | 0 | 425 | 112 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### unauthorized_scope
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 32 | 48 | 1 | 0 |
| no | 158 | 329 | 0 | 0 |
| not_applicable | 13 | 19 | 0 | 0 |

### sensitive_data_exposure
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 13 | 33 | 2 | 0 |
| no | 12 | 101 | 4 | 0 |
| not_applicable | 84 | 225 | 126 | 0 |

### untrusted_destination
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 33 | 2 | 50 | 0 |
| no | 46 | 74 | 21 | 0 |
| not_applicable | 34 | 0 | 340 | 0 |

### privilege_escalation
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 38 | 0 | 0 | 0 |
| no | 7 | 551 | 4 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### destructive_or_irreversible_action
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 42 | 26 | 0 | 0 |
| no | 31 | 501 | 0 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### financial_commitment
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 10 | 40 | 0 | 0 |
| no | 2 | 46 | 502 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### external_communication
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 20 | 1 | 0 | 0 |
| no | 18 | 3 | 0 | 0 |
| not_applicable | 42 | 334 | 182 | 0 |

### policy_conflict
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 14 | 163 | 51 | 0 |
| no | 14 | 267 | 74 | 0 |
| not_applicable | 0 | 1 | 16 | 0 |

### suspicious_action_sequence
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 42 | 7 | 0 | 0 |
| no | 43 | 50 | 0 | 0 |
| not_applicable | 36 | 222 | 200 | 0 |

### insufficient_context
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 17 | 41 | 0 | 0 |
| no | 202 | 340 | 0 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |
