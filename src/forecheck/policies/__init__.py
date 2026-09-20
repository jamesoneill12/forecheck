"""The deterministic policy engine: scores plus context facts in, ``ALLOW`` /
``REVIEW`` / ``DENY`` out, always the same answer for the same input.

See :mod:`forecheck.policies.base` for the interface, :mod:`forecheck.policies.dsl` for
the YAML rule schema, :mod:`forecheck.policies.engine` for the evaluator, and
:mod:`forecheck.policies.loader` / :mod:`forecheck.policies.builtin` for turning a YAML
file into a running engine.
"""

from __future__ import annotations

from forecheck.policies.base import PolicyEngine, PolicyEngineBase
from forecheck.policies.builtin import (
    available_bundle_names,
    builtin_bundle_path,
    load_builtin_engine,
)
from forecheck.policies.dsl import Condition, FactValue, PolicyBundle, Rule, UnknownAs
from forecheck.policies.engine import (
    FACT_NAMES,
    DeterministicPolicyEngine,
    FactTable,
    combine_matched_rules,
    derive_facts,
)
from forecheck.policies.loader import (
    hash_bundle,
    load_bundle_file,
    load_bundle_yaml,
    load_policy_engine,
    validate_fact_references,
)

__all__ = [
    "FACT_NAMES",
    "Condition",
    "DeterministicPolicyEngine",
    "FactTable",
    "FactValue",
    "PolicyBundle",
    "PolicyEngine",
    "PolicyEngineBase",
    "Rule",
    "UnknownAs",
    "available_bundle_names",
    "builtin_bundle_path",
    "combine_matched_rules",
    "derive_facts",
    "hash_bundle",
    "load_builtin_engine",
    "load_bundle_file",
    "load_bundle_yaml",
    "load_policy_engine",
    "validate_fact_references",
]
