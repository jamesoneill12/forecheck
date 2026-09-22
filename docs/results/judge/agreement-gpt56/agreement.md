# forecheck LLM-judge agreement — gpt-5.6-sol

n_examples=600

| dimension | n_compared | n_unparseable | agreement | kappa |
|---|---|---|---|---|
| prompt_injection_influence | 600 | 0 | 0.7833 | 0.3901 |
| unauthorized_scope | 600 | 0 | 0.7883 | 0.4243 |
| sensitive_data_exposure | 600 | 0 | 0.3833 | 0.1377 |
| untrusted_destination | 600 | 0 | 0.7383 | 0.4944 |
| privilege_escalation | 600 | 0 | 0.9850 | 0.8863 |
| destructive_or_irreversible_action | 600 | 0 | 0.8967 | 0.5109 |
| financial_commitment | 600 | 0 | 0.1167 | -0.0374 |
| external_communication | 600 | 0 | 0.3400 | 0.0442 |
| policy_conflict | 600 | 0 | 0.8417 | 0.6990 |
| suspicious_action_sequence | 600 | 0 | 0.4983 | 0.2363 |
| insufficient_context | 600 | 0 | 0.8433 | 0.0595 |

## Confusion (generator row vs judge column)

### prompt_injection_influence
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 53 | 9 | 1 | 0 |
| no | 0 | 417 | 120 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### unauthorized_scope
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 60 | 21 | 0 | 0 |
| no | 74 | 413 | 0 | 0 |
| not_applicable | 25 | 7 | 0 | 0 |

### sensitive_data_exposure
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 8 | 39 | 1 | 0 |
| no | 15 | 101 | 1 | 0 |
| not_applicable | 75 | 239 | 121 | 0 |

### untrusted_destination
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 35 | 1 | 49 | 0 |
| no | 49 | 69 | 23 | 0 |
| not_applicable | 35 | 0 | 339 | 0 |

### privilege_escalation
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 38 | 0 | 0 | 0 |
| no | 7 | 553 | 2 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### destructive_or_irreversible_action
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 41 | 27 | 0 | 0 |
| no | 35 | 497 | 0 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### financial_commitment
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 12 | 38 | 0 | 0 |
| no | 1 | 58 | 491 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |

### external_communication
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 18 | 3 | 0 | 0 |
| no | 19 | 2 | 0 | 0 |
| not_applicable | 40 | 334 | 184 | 0 |

### policy_conflict
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 202 | 24 | 2 | 0 |
| no | 56 | 288 | 11 | 0 |
| not_applicable | 1 | 1 | 15 | 0 |

### suspicious_action_sequence
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 40 | 9 | 0 | 0 |
| no | 34 | 59 | 0 | 0 |
| not_applicable | 46 | 212 | 200 | 0 |

### insufficient_context
| generator \ judge | yes | no | not_applicable | unparseable |
|---|---|---|---|---|
| yes | 8 | 50 | 0 | 0 |
| no | 44 | 498 | 0 | 0 |
| not_applicable | 0 | 0 | 0 | 0 |
