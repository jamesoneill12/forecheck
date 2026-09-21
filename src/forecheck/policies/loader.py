"""Load, validate and hash policy bundles.

This is the only layer in :mod:`forecheck.policies` that touches the filesystem or a
YAML parser. Everything it produces (a :class:`~forecheck.policies.dsl.PolicyBundle`, a
hash, a :class:`~forecheck.policies.engine.DeterministicPolicyEngine`) is then consumed
by pure code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from forecheck.contracts import ErrorCode, ForecheckError
from forecheck.policies.dsl import Condition, PolicyBundle
from forecheck.policies.engine import FACT_NAMES, DeterministicPolicyEngine
from forecheck.version import POLICY_DSL_VERSION

__all__ = [
    "hash_bundle",
    "load_bundle_file",
    "load_bundle_yaml",
    "load_policy_engine",
    "validate_fact_references",
]


def _collect_fact_names(condition: Condition, into: set[str]) -> None:
    if condition.all_ is not None:
        for child in condition.all_:
            _collect_fact_names(child, into)
        return
    if condition.any_ is not None:
        for child in condition.any_:
            _collect_fact_names(child, into)
        return
    if condition.not_ is not None:
        _collect_fact_names(condition.not_, into)
        return
    if condition.fact is not None:
        into.add(condition.fact)


def validate_fact_references(bundle: PolicyBundle) -> None:
    """Reject a bundle that names a fact the engine does not know about.

    An unrecognised ``score`` is already a load-time error for free, because
    :class:`~forecheck.contracts.RiskDimension` is a closed enum that Pydantic
    validates while parsing. Fact names are plain strings, so they need this explicit
    pass, run separately so :mod:`forecheck.policies.dsl` never has to import
    :mod:`forecheck.policies.engine`.
    """
    referenced: set[str] = set()
    for rule in bundle.rules:
        _collect_fact_names(rule.when, referenced)
    unknown = referenced - FACT_NAMES
    if unknown:
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_INVALID,
            f"bundle {bundle.bundle_id!r} references unknown fact(s): {sorted(unknown)}",
            field_path="rules[].when.fact",
        )


def _validate_dsl_version(bundle: PolicyBundle) -> None:
    # Only a major-version mismatch rejects; minor bumps are additive (ADR 0002).
    bundle_major = bundle.dsl_version.split(".", 1)[0]
    engine_major = POLICY_DSL_VERSION.split(".", 1)[0]
    if bundle_major != engine_major:
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_INVALID,
            f"bundle {bundle.bundle_id!r} declares dsl_version "
            f"{bundle.dsl_version!r}, this engine supports {POLICY_DSL_VERSION!r}",
            field_path="dsl_version",
        )


def _canonical_bytes(bundle: PolicyBundle) -> bytes:
    payload: dict[str, Any] = bundle.model_dump(mode="json", by_alias=True)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_bundle(bundle: PolicyBundle) -> str:
    """Sha256 of the canonical, sorted-key JSON serialisation of the bundle.

    Two bundles with identical semantics but re-ordered mapping keys hash the same;
    re-ordering the ``rules`` list itself changes the hash, since rule order is part of
    what a bundle_hash in an audit log should be able to pin.
    """
    return hashlib.sha256(_canonical_bytes(bundle)).hexdigest()


def load_bundle_yaml(text: str, *, source: str = "<string>") -> PolicyBundle:
    """Parse, structurally validate and fact-check a policy bundle from YAML text."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_INVALID, f"{source}: invalid YAML: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_INVALID,
            f"{source}: a policy bundle must be a YAML mapping at the top level",
        )
    try:
        bundle = PolicyBundle.model_validate(raw)
    except ValidationError as exc:
        raise ForecheckError(ErrorCode.POLICY_BUNDLE_INVALID, f"{source}: {exc}") from exc
    _validate_dsl_version(bundle)
    validate_fact_references(bundle)
    return bundle


def load_bundle_file(path: Path) -> PolicyBundle:
    return load_bundle_yaml(path.read_text(encoding="utf-8"), source=str(path))


def load_policy_engine(path: Path) -> DeterministicPolicyEngine:
    bundle = load_bundle_file(path)
    return DeterministicPolicyEngine(bundle, hash_bundle(bundle))
