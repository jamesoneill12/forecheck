"""JSONL persistence for :class:`Example` rows, plus checksummed dataset manifests."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from forecheck.contracts import (
    DatasetManifest,
    Example,
    LabelValue,
    PolicyPredicateKind,
    RiskDimension,
    Split,
)

__all__ = [
    "build_manifest",
    "read_jsonl",
    "sha256_file",
    "verify_manifest",
    "write_jsonl",
    "write_manifests",
]

_HASH_CHUNK_BYTES = 1 << 20


def write_jsonl(path: Path, examples: Iterable[Example]) -> None:
    """Write ``examples`` to ``path`` as one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(example.model_dump_json())
            handle.write("\n")


def read_jsonl(path: Path) -> list[Example]:
    """Read a JSONL file of :class:`Example` rows written by :func:`write_jsonl`."""
    if not path.exists():
        return []
    examples: list[Example] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                examples.append(Example.model_validate_json(stripped))
    return examples


def sha256_file(path: Path) -> str:
    """Digest of a file's bytes, streamed so large shards do not need to fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_rate(examples: Sequence[Example]) -> dict[RiskDimension, float]:
    rates: dict[RiskDimension, float] = {}
    for dimension in RiskDimension:
        applicable = [
            e for e in examples if e.labels.values[dimension] is not LabelValue.NOT_APPLICABLE
        ]
        if not applicable:
            rates[dimension] = 0.0
            continue
        positives = sum(1 for e in applicable if e.labels.values[dimension] is LabelValue.YES)
        rates[dimension] = positives / len(applicable)
    return rates


def build_manifest(
    split: Split,
    path: Path,
    examples: Sequence[Example],
    *,
    heldout_policy_kinds: frozenset[PolicyPredicateKind] = frozenset(),
) -> DatasetManifest:
    """Build a checksummed :class:`DatasetManifest` describing ``path``.

    ``path`` must already contain ``examples`` written via :func:`write_jsonl`.
    ``heldout_policy_kinds`` records the kinds withheld for this dataset (ADR 0011),
    regardless of ``split``, so the withheld set is auditable from any one manifest file.
    """
    family_ids = sorted({e.family_id for e in examples})
    family_ids_digest = hashlib.sha256("\n".join(family_ids).encode()).hexdigest()
    generator_versions = sorted({e.provenance.generator_version for e in examples})
    return DatasetManifest(
        split=split,
        path=str(path),
        n_examples=len(examples),
        n_families=len(family_ids),
        sha256=sha256_file(path),
        generator_versions=generator_versions,
        created_at=datetime.now(tz=UTC),
        positive_rate=_positive_rate(examples),
        family_ids_sha256=family_ids_digest,
        heldout_policy_kinds=sorted(k.value for k in heldout_policy_kinds),
    )


def write_manifests(directory: Path, manifests: Iterable[DatasetManifest]) -> None:
    """Write one ``<split>.manifest.json`` file per manifest into ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    for manifest in manifests:
        target = directory / f"{manifest.split.value}.manifest.json"
        target.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def verify_manifest(manifest: DatasetManifest, path: Path) -> bool:
    """Return ``True`` iff ``path`` still hashes to what ``manifest`` recorded."""
    return sha256_file(path) == manifest.sha256
