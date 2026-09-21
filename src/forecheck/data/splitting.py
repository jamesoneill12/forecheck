"""Leakage-safe dataset splitting.

Splitting has two independent tiers:

1. **Heldout-family tier.** A deterministic hash of each example's ``family_id``
   (a whole tool, e.g. ``email.send_message``) decides whether *every* row for that
   family goes to :attr:`Split.HELDOUT_FAMILY`, at ``HELDOUT_FAMILY_RATIO`` of
   families. This guarantees some tools are entirely unseen in training and
   evaluated as a block.
2. **Group tier.** Everything not pulled into the heldout-family tier is split at
   finer grain, by the root of ``template_lineage`` (one base scenario and its
   contrastive derivatives) via :func:`assign_split`, over train / calibration /
   dev / test / adversarial. This keeps individual scenarios, not just whole
   tools, out of both train and eval.

Both hashes are deterministic, so the same input always produces the same split
without keeping any state around.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from forecheck.contracts import Example, LatentScenario, Split, UsageRestriction

__all__ = [
    "DEFAULT_SALT",
    "HELDOUT_FAMILY_RATIO",
    "SPLIT_RATIOS",
    "IneligibleForSplitError",
    "LeakageError",
    "assert_no_leakage",
    "assign_split",
    "compute_group_key",
    "is_heldout_family",
    "split_examples",
]

DEFAULT_SALT = "forecheck-split-v1"

"""Fraction of families (whole tools) withheld via :func:`is_heldout_family`."""
HELDOUT_FAMILY_RATIO = 0.05

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


def is_heldout_family(family_id: str, *, salt: str = DEFAULT_SALT) -> bool:
    """Whether every example of ``family_id`` is withheld as :attr:`Split.HELDOUT_FAMILY`."""
    digest = hashlib.sha256(f"{salt}:heldout:{family_id}".encode()).hexdigest()
    fraction = int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
    return fraction < HELDOUT_FAMILY_RATIO


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
    examples: Sequence[Example], *, salt: str = DEFAULT_SALT
) -> dict[Split, list[Example]]:
    """Assign every example to a split, family- then group-wise, refusing ineligible rows.

    Every row of a family pulled into :attr:`Split.HELDOUT_FAMILY` by
    :func:`is_heldout_family` lands there; everything else is assigned by
    :func:`assign_split` over its group key. Both halves of a contrastive pair
    always land in the same split: the second occurrence of a
    ``contrastive_pair_id`` reuses the split already assigned to the first,
    regardless of its own family or group key.
    """
    pair_split: dict[str, Split] = {}
    result: dict[Split, list[Example]] = {split: [] for split in Split}

    for example in examples:
        pair_id = example.contrastive_pair_id
        if pair_id is not None and pair_id in pair_split:
            split = pair_split[pair_id]
        elif is_heldout_family(example.latent.family_id, salt=salt):
            split = Split.HELDOUT_FAMILY
        else:
            split = assign_split(compute_group_key(example.latent), salt=salt)

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
