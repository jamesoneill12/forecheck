"""Loading, cross-referencing and hashing policy bundles."""

from __future__ import annotations

from pathlib import Path

import pytest

from forecheck.contracts import ErrorCode, ForecheckError
from forecheck.policies.builtin import (
    available_bundle_names,
    builtin_bundle_path,
    load_builtin_engine,
)
from forecheck.policies.loader import hash_bundle, load_bundle_file, load_bundle_yaml

MINIMAL_VALID_YAML = """
bundle_id: minimal
version: 1
dsl_version: "1.0"
description: minimal test bundle
default_decision: review
rules:
  - id: r1
    description: a rule
    decision: deny
    hard: true
    when:
      score: prompt_injection_influence
      gte: 0.5
"""


def test_load_minimal_bundle() -> None:
    bundle = load_bundle_yaml(MINIMAL_VALID_YAML)
    assert bundle.bundle_id == "minimal"
    assert len(bundle.rules) == 1


def test_load_rejects_unknown_fact_name() -> None:
    yaml_text = MINIMAL_VALID_YAML.replace(
        "when:\n      score: prompt_injection_influence\n      gte: 0.5",
        "when:\n      fact: not_a_real_fact\n      is: true",
    )
    with pytest.raises(ForecheckError) as excinfo:
        load_bundle_yaml(yaml_text)
    assert excinfo.value.code is ErrorCode.POLICY_BUNDLE_INVALID
    assert "not_a_real_fact" in excinfo.value.message


def test_load_rejects_wrong_dsl_version() -> None:
    yaml_text = MINIMAL_VALID_YAML.replace('dsl_version: "1.0"', 'dsl_version: "99.0"')
    with pytest.raises(ForecheckError) as excinfo:
        load_bundle_yaml(yaml_text)
    assert excinfo.value.code is ErrorCode.POLICY_BUNDLE_INVALID


def test_load_rejects_invalid_yaml() -> None:
    with pytest.raises(ForecheckError):
        load_bundle_yaml("not: valid: yaml: [")


def test_load_rejects_non_mapping_top_level() -> None:
    with pytest.raises(ForecheckError):
        load_bundle_yaml("- just\n- a\n- list\n")


def test_hash_is_stable_across_loads() -> None:
    bundle_a = load_bundle_yaml(MINIMAL_VALID_YAML)
    bundle_b = load_bundle_yaml(MINIMAL_VALID_YAML)
    assert hash_bundle(bundle_a) == hash_bundle(bundle_b)
    assert len(hash_bundle(bundle_a)) == 64


def test_hash_changes_with_content() -> None:
    changed = MINIMAL_VALID_YAML.replace("gte: 0.5", "gte: 0.6")
    bundle_a = load_bundle_yaml(MINIMAL_VALID_YAML)
    bundle_b = load_bundle_yaml(changed)
    assert hash_bundle(bundle_a) != hash_bundle(bundle_b)


@pytest.mark.parametrize("name", ["conservative", "balanced", "permissive"])
def test_builtin_bundles_load_and_hash_stably(name: str, policies_dir: Path) -> None:
    path = policies_dir / f"{name}.yaml"
    bundle_a = load_bundle_file(path)
    bundle_b = load_bundle_file(path)
    assert bundle_a.bundle_id == name
    assert hash_bundle(bundle_a) == hash_bundle(bundle_b)


@pytest.mark.parametrize("name", ["conservative", "balanced", "permissive"])
def test_builtin_engine_accessor(name: str) -> None:
    engine = load_builtin_engine(name)
    assert engine.bundle_id == name
    assert len(engine.bundle_hash) == 64


def test_available_bundle_names() -> None:
    assert available_bundle_names() == ("balanced", "conservative", "permissive")


def test_unknown_builtin_bundle_name_raises() -> None:
    with pytest.raises(KeyError):
        builtin_bundle_path("nonexistent")
