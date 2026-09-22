"""Leakage-safe dataset splitting.

Splitting has two independent tiers:

1. **Heldout-family tier.** Whole tools (``family_id``, e.g. ``email.send_message``)
   are withheld so *every* row for them goes to :attr:`Split.HELDOUT_FAMILY`.
   Selection is stratified by operation kind at ``HELDOUT_FAMILY_RATIO``, ranking
   tools by a deterministic hash within each kind, so each operation (and the label
   dimensions it drives, e.g. grant -> privilege_escalation) has at least one tool
   entirely unseen in training. The first GPU run withheld three tools by plain
   hash and had zero privilege_escalation positives to evaluate on. Two policy
   heldout tiers (kind, phrasing; see ADR 0010, and ADR 0011 for the configurable
   withheld-kind count) sit above this one; see :func:`split_examples`.
2. **Group tier.** Everything not pulled into an earlier tier is split at
   finer grain, by the root of ``template_lineage`` (one base scenario and its
   contrastive derivatives) via :func:`assign_split`, over train / calibration /
   dev / test / adversarial. This keeps individual scenarios, not just whole
   tools, out of both train and eval.

Both hashes are deterministic, so the same input always produces the same split
without keeping any state around.
"""

from __future__ import annotations

import functools
import hashlib
from collections import defaultdict
from collections.abc import Sequence

from forecheck.contracts import (
    Example,
    LatentScenario,
    OperationKind,
    PolicyPredicate,
    PolicyPredicateKind,
    Split,
    UsageRestriction,
)
from forecheck.data.tools import TOOL_CATALOGUE

__all__ = [
    "DEFAULT_HELDOUT_POLICY_KIND_COUNT",
    "DEFAULT_SALT",
    "HELDOUT_FAMILY_RATIO",
    "HELDOUT_PARAPHRASE_INDICES",
    "HELDOUT_POLICY_KINDS",
    "PAIR_SPLIT_RATIOS",
    "SPLIT_RATIOS",
    "IneligibleForSplitError",
    "LeakageError",
    "assert_no_leakage",
    "assign_pair_split",
    "assign_split",
    "compute_group_key",
    "default_heldout_policy_kinds",
    "is_heldout_family",
    "split_examples",
]

DEFAULT_SALT = "forecheck-split-v1"

"""How many :class:`PolicyPredicateKind` members :func:`default_heldout_policy_kinds`
withholds by default. Raised from 2 to 4 for ADR 0011 (v5): with 30 kinds total,
withholding 4 still leaves 26 for the model to generalise the *shape* of a policy kind
from, rather than memorise the 2 remaining ones by exclusion."""
DEFAULT_HELDOUT_POLICY_KIND_COUNT = 4


def _kind_heldout_fraction(kind: PolicyPredicateKind, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:heldout_kind:{kind.value}".encode()).hexdigest()
    return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


def default_heldout_policy_kinds(
    n: int = DEFAULT_HELDOUT_POLICY_KIND_COUNT, *, salt: str = DEFAULT_SALT
) -> frozenset[PolicyPredicateKind]:
    """Deterministically choose ``n`` kinds to withhold from train/calibration/dev/test.

    Kinds are ranked by a salted hash of their value, so the choice is stable across
    runs (and processes) for a given ``(n, salt)`` without keeping any state, and callers
    needing a different withheld set for an experiment can pass a different ``n`` or
    ``salt`` (see ADR 0011).
    """
    ranked = sorted(PolicyPredicateKind, key=lambda kind: _kind_heldout_fraction(kind, salt))
    return frozenset(ranked[:n])


"""Default withheld-kind set, used when :func:`split_examples` is not given an explicit
override; see ADR 0010 (original 2-kind set) and ADR 0011 (raised to 4)."""
HELDOUT_POLICY_KINDS: frozenset[PolicyPredicateKind] = default_heldout_policy_kinds()

"""Clause paraphrase indices withheld from train for kinds that ARE trained, so
`heldout_policy_phrasing` measures generalisation to unseen *wording* of a familiar
policy kind (see ADR 0010)."""
HELDOUT_PARAPHRASE_INDICES: frozenset[int] = frozenset({3})

"""Fraction of families (whole tools) withheld via :func:`is_heldout_family`."""
HELDOUT_FAMILY_RATIO = 0.12

_BASE_RATIOS: dict[Split, float] = {
    Split.TRAIN: 0.60,
    Split.CALIBRATION: 0.10,
    Split.DEV: 0.10,
    Split.TEST: 0.10,
    Split.ADVERSARIAL: 0.05,
}
_BASE_TOTAL = sum(_BASE_RATIOS.values())
SPLIT_RATIOS: dict[Split, float] = {
    split: ratio / _BASE_TOTAL for split, ratio in _BASE_RATIOS.items()
}

_SPLIT_ORDER: tuple[Split, ...] = tuple(SPLIT_RATIOS)

"""Contrastive pairs are deliberately routed with their own, eval-heavy ratio table:
the bulk-scenario ratios above would scatter most pairs into train, and a handful of
pairs per axis is not enough to reliably clear a per-split coverage floor under that
distribution. Skewing pairs toward calibration/dev/test/adversarial makes a modest
``pairs_per_axis`` still land enough of each axis in every eval split."""
_PAIR_BASE_RATIOS: dict[Split, float] = {
    Split.TRAIN: 0.10,
    Split.CALIBRATION: 0.275,
    Split.DEV: 0.275,
    Split.TEST: 0.275,
    Split.ADVERSARIAL: 0.075,
}
_PAIR_TOTAL = sum(_PAIR_BASE_RATIOS.values())
PAIR_SPLIT_RATIOS: dict[Split, float] = {
    split: ratio / _PAIR_TOTAL for split, ratio in _PAIR_BASE_RATIOS.items()
}


class LeakageError(RuntimeError):
    """A group or contrastive pair straddled more than one split."""


class IneligibleForSplitError(RuntimeError):
    """An example's licence forbids it from the requested split."""


def compute_group_key(latent: LatentScenario) -> str:
    """The unit splits are assigned to: the root of the template lineage, or the
    scenario's family id when no lineage is recorded."""
    if latent.template_lineage:
        return latent.template_lineage[0]
    return latent.family_id


def _heldout_fraction(family_id: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:heldout:{family_id}".encode()).hexdigest()
    return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


@functools.lru_cache(maxsize=8)
def _heldout_catalogue_families(salt: str) -> frozenset[str]:
    """Catalogue tools withheld under ``salt``: within each operation kind, the
    ``max(1, round(HELDOUT_FAMILY_RATIO * n))`` lowest-hashing tools, so every
    operation (and hence every label dimension it drives) has an unseen tool."""
    by_operation: dict[OperationKind, list[str]] = defaultdict(list)
    for tool in TOOL_CATALOGUE:
        by_operation[tool.operation].append(f"{tool.family.value}:{tool.name}")
    withheld: set[str] = set()
    for family_ids in by_operation.values():
        k = max(1, round(HELDOUT_FAMILY_RATIO * len(family_ids)))
        ranked = sorted(family_ids, key=lambda fid: _heldout_fraction(fid, salt))
        withheld.update(ranked[:k])
    return frozenset(withheld)


def is_heldout_family(family_id: str, *, salt: str = DEFAULT_SALT) -> bool:
    """Whether every example of ``family_id`` is withheld as :attr:`Split.HELDOUT_FAMILY`.

    Catalogue tools are selected per operation kind (see
    :func:`_heldout_catalogue_families`); family ids outside the catalogue fall back
    to a plain hash threshold at :data:`HELDOUT_FAMILY_RATIO`.
    """
    catalogue = _heldout_catalogue_families(salt)
    if family_id in catalogue:
        return True
    if family_id in _CATALOGUE_FAMILY_IDS:
        return False
    return _heldout_fraction(family_id, salt) < HELDOUT_FAMILY_RATIO


_CATALOGUE_FAMILY_IDS: frozenset[str] = frozenset(
    f"{tool.family.value}:{tool.name}" for tool in TOOL_CATALOGUE
)


def assign_split(group_key: str, *, salt: str = DEFAULT_SALT) -> Split:
    """Deterministically assign ``group_key`` to a :class:`Split` by fixed ratio."""
    digest = hashlib.sha256(f"{salt}:{group_key}".encode()).hexdigest()
    fraction = int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
    cumulative = 0.0
    for split in _SPLIT_ORDER:
        cumulative += SPLIT_RATIOS[split]
        if fraction < cumulative:
            return split
    return _SPLIT_ORDER[-1]


def _predicate_kind_is_heldout(
    pred: PolicyPredicate, heldout_kinds: frozenset[PolicyPredicateKind]
) -> bool:
    return pred.kind in heldout_kinds


def _predicate_phrasing_is_heldout(
    pred: PolicyPredicate, heldout_kinds: frozenset[PolicyPredicateKind]
) -> bool:
    return pred.kind not in heldout_kinds and pred.paraphrase_index in HELDOUT_PARAPHRASE_INDICES


def assign_pair_split(group_key: str, *, salt: str = DEFAULT_SALT) -> Split:
    """Deterministically assign a contrastive pair's ``group_key`` using
    :data:`PAIR_SPLIT_RATIOS`, so eval splits reliably get pair coverage per axis."""
    digest = hashlib.sha256(f"{salt}:pair:{group_key}".encode()).hexdigest()
    fraction = int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
    cumulative = 0.0
    for split in _SPLIT_ORDER:
        cumulative += PAIR_SPLIT_RATIOS.get(split, 0.0)
        if fraction < cumulative:
            return split
    return Split.TEST


def _check_license_eligibility(example: Example, split: Split) -> None:
    if split not in (Split.TRAIN, Split.CALIBRATION):
        return
    if example.license.usage is UsageRestriction.EVAL_ONLY:
        raise IneligibleForSplitError(
            f"example {example.example_id!r} is eval_only and cannot enter {split.value}"
        )
    if example.license.canary_present:
        raise IneligibleForSplitError(
            f"example {example.example_id!r} carries a canary and cannot enter {split.value}"
        )


def split_examples(
    examples: Sequence[Example],
    *,
    salt: str = DEFAULT_SALT,
    heldout_policy_kinds: frozenset[PolicyPredicateKind] | None = None,
) -> dict[Split, list[Example]]:
    """Assign every example to a split, family- then group-wise, refusing ineligible rows.

    Every row of a family pulled into :attr:`Split.HELDOUT_FAMILY` by
    :func:`is_heldout_family` lands there. Otherwise, a group carrying a predicate whose
    kind is in ``heldout_policy_kinds`` (defaults to :data:`HELDOUT_POLICY_KINDS`, see
    :func:`default_heldout_policy_kinds`) lands entirely in
    :attr:`Split.HELDOUT_POLICY_KIND`; a group carrying a predicate of a trained kind
    but a withheld paraphrase (:data:`HELDOUT_PARAPHRASE_INDICES`) lands entirely in
    :attr:`Split.HELDOUT_POLICY_PHRASING` (see ADR 0010, ADR 0011). A row whose group is
    one of a contrastive pair (i.e. some row sharing its group key carries a
    ``contrastive_pair_id``, whether or not this particular row does) is assigned by
    :func:`assign_pair_split`; every other row is assigned by :func:`assign_split`. Both
    halves of a contrastive pair always land in the same split: only ``make_pair``
    derived rows are required to carry ``contrastive_pair_id`` (see :class:`Example`),
    but base and derived rows always share a group key, so routing on the group key --
    not the per-row flag -- keeps them together even when only one of the two rows is
    tagged.
    """
    heldout_kinds = (
        heldout_policy_kinds if heldout_policy_kinds is not None else HELDOUT_POLICY_KINDS
    )
    pair_group_keys = {
        compute_group_key(example.latent)
        for example in examples
        if example.contrastive_pair_id is not None
    }
    policy_kind_heldout_groups = {
        compute_group_key(example.latent)
        for example in examples
        if any(
            _predicate_kind_is_heldout(p, heldout_kinds) for p in example.latent.policy_predicates
        )
    }
    policy_phrasing_heldout_groups = {
        compute_group_key(example.latent)
        for example in examples
        if any(
            _predicate_phrasing_is_heldout(p, heldout_kinds)
            for p in example.latent.policy_predicates
        )
    }
    pair_split: dict[str, Split] = {}
    result: dict[Split, list[Example]] = {split: [] for split in Split}

    for example in examples:
        pair_id = example.contrastive_pair_id
        group_key = compute_group_key(example.latent)
        if pair_id is not None and pair_id in pair_split:
            split = pair_split[pair_id]
        elif is_heldout_family(example.latent.family_id, salt=salt):
            split = Split.HELDOUT_FAMILY
        elif group_key in policy_kind_heldout_groups:
            split = Split.HELDOUT_POLICY_KIND
        elif group_key in policy_phrasing_heldout_groups:
            split = Split.HELDOUT_POLICY_PHRASING
        elif group_key in pair_group_keys:
            split = assign_pair_split(group_key, salt=salt)
        else:
            split = assign_split(group_key, salt=salt)

        if pair_id is not None and pair_id not in pair_split:
            pair_split[pair_id] = split

        _check_license_eligibility(example, split)
        result[split].append(example.model_copy(update={"split": split}))

    return result


def assert_no_leakage(splits: dict[Split, list[Example]]) -> None:
    """Raise :class:`LeakageError` if any group, family, or contrastive pair spans splits."""
    group_to_split: dict[str, Split] = {}
    pair_to_split: dict[str, Split] = {}
    family_to_split: dict[str, Split] = {}
    for split, rows in splits.items():
        for row in rows:
            group_key = compute_group_key(row.latent)
            seen_split = group_to_split.get(group_key)
            if seen_split is None:
                group_to_split[group_key] = split
            elif seen_split is not split:
                raise LeakageError(
                    f"group {group_key!r} appears in both {seen_split.value} and {split.value}"
                )
            if row.contrastive_pair_id is not None:
                seen_pair_split = pair_to_split.get(row.contrastive_pair_id)
                if seen_pair_split is None:
                    pair_to_split[row.contrastive_pair_id] = split
                elif seen_pair_split is not split:
                    raise LeakageError(
                        f"contrastive pair {row.contrastive_pair_id!r} straddles "
                        f"{seen_pair_split.value} and {split.value}"
                    )
            family_id = row.latent.family_id
            seen_family_split = family_to_split.get(family_id)
            if seen_family_split is None:
                family_to_split[family_id] = split
            elif seen_family_split is not split and Split.HELDOUT_FAMILY in (
                seen_family_split,
                split,
            ):
                raise LeakageError(
                    f"family {family_id!r} appears in both {seen_family_split.value} "
                    f"and {split.value}"
                )
