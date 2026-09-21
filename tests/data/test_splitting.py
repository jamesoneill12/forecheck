from __future__ import annotations

import collections
import random
from datetime import UTC, datetime

import pytest

from forecheck.contracts import (
    ContrastiveAxis,
    Example,
    LabelSet,
    LabelValue,
    PolicyPredicate,
    PolicyPredicateKind,
    Provenance,
    RiskDimension,
    SourceLicense,
    Split,
    Transformation,
    UsageRestriction,
)
from forecheck.data.contrastive import contrastive_pair_id, make_pair
from forecheck.data.rendering import OfflineTemplateRenderer
from forecheck.data.splitting import (
    HELDOUT_PARAPHRASE_INDICES,
    HELDOUT_POLICY_KINDS,
    IneligibleForSplitError,
    LeakageError,
    assert_no_leakage,
    assign_pair_split,
    assign_split,
    compute_group_key,
    is_heldout_family,
    split_examples,
)
from forecheck.version import LABEL_DERIVATION_VERSION
from tests.data.factories import make_latent


def _example_for(latent: object, **overrides: object) -> Example:
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    values = dict.fromkeys(RiskDimension, LabelValue.NO)
    labels = LabelSet(values=values, derivation_version=LABEL_DERIVATION_VERSION)
    provenance = Provenance(
        generator_name="test",
        generator_version="0.0.1",
        seed=0,
        created_at=datetime.now(tz=UTC),
    )
    defaults: dict[str, object] = {
        "example_id": f"ex-{latent.scenario_id}",
        "family_id": latent.family_id,
        "latent": latent,
        "context": context,
        "labels": labels,
        "provenance": provenance,
    }
    defaults.update(overrides)
    return Example(**defaults)


def test_group_key_uses_lineage_root() -> None:
    latent = make_latent(family_id="fam-a", template_lineage=["root-x", "leaf-y"])
    assert compute_group_key(latent) == "root-x"


def test_group_key_falls_back_to_family_id() -> None:
    latent = make_latent(family_id="fam-a", template_lineage=[])
    assert compute_group_key(latent) == "fam-a"


def test_assign_split_is_deterministic() -> None:
    assert assign_split("group-1") == assign_split("group-1")


def test_assign_split_covers_every_split_over_many_groups() -> None:
    seen = {assign_split(f"group-{i}") for i in range(500)}
    assert seen == {
        Split.TRAIN,
        Split.CALIBRATION,
        Split.DEV,
        Split.TEST,
        Split.ADVERSARIAL,
    }


def test_split_examples_keeps_contrastive_pairs_together() -> None:
    base = make_latent(scenario_id="base-1")
    flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
    pair_id = contrastive_pair_id(base.scenario_id, ContrastiveAxis.RESOURCE_SENSITIVITY)
    transformation = Transformation(
        axis=ContrastiveAxis.RESOURCE_SENSITIVITY,
        base_example_id="ex-base-1",
        from_value="internal",
        to_value="restricted",
    )
    examples = [
        _example_for(base, example_id="ex-base-1"),
        _example_for(
            flipped,
            example_id="ex-flip-1",
            family_id=base.family_id,
            contrastive_pair_id=pair_id,
            transformation=transformation,
        ),
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    found = [split for split, rows in splits.items() if rows]
    assert len(found) == 1


def test_assign_pair_split_favors_eval_over_train() -> None:
    counts = collections.Counter(assign_pair_split(f"group-{i}") for i in range(2000))
    assert counts[Split.CALIBRATION] > counts[Split.TRAIN]
    assert counts[Split.DEV] > counts[Split.TRAIN]
    assert counts[Split.TEST] > counts[Split.TRAIN]


def test_pair_group_routes_through_pair_ratios() -> None:
    """Only the transformed row of each pair carries ``contrastive_pair_id`` (matching
    the real contract), yet the pair-heavy eval ratios still apply to the whole group."""
    examples: list[Example] = []
    for i in range(300):
        base = make_latent(
            scenario_id=f"base-{i}",
            family_id=f"fam-pair-{i}",
            template_lineage=[f"fam-pair-{i}#base-{i}"],
        )
        flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
        pair_id = contrastive_pair_id(base.scenario_id, ContrastiveAxis.RESOURCE_SENSITIVITY)
        transformation = Transformation(
            axis=ContrastiveAxis.RESOURCE_SENSITIVITY,
            base_example_id=f"ex-base-{i}",
            from_value="internal",
            to_value="restricted",
        )
        examples.append(_example_for(base, example_id=f"ex-base-{i}"))
        examples.append(
            _example_for(
                flipped,
                example_id=f"ex-flip-{i}",
                family_id=base.family_id,
                contrastive_pair_id=pair_id,
                transformation=transformation,
            )
        )
    splits = split_examples(examples)
    assert_no_leakage(splits)
    eval_rows = len(splits[Split.CALIBRATION]) + len(splits[Split.DEV]) + len(splits[Split.TEST])
    assert eval_rows > len(splits[Split.TRAIN])


def test_split_examples_refuses_eval_only_when_routed_to_train() -> None:
    latent = make_latent(family_id="force-train")
    example = _example_for(latent, license=SourceLicense(usage=UsageRestriction.EVAL_ONLY))
    salt = "salt"
    group_key = compute_group_key(latent)
    target_split = assign_split(group_key, salt=salt)
    if target_split not in (Split.TRAIN, Split.CALIBRATION):
        pytest.skip("chosen salt does not route this group into train/calibration")
    with pytest.raises(IneligibleForSplitError):
        split_examples([example], salt=salt)


def test_assert_no_leakage_raises_on_group_split_across_splits() -> None:
    latent_a = make_latent(scenario_id="a", family_id="shared-group")
    latent_b = make_latent(scenario_id="b", family_id="shared-group")
    example_a = _example_for(latent_a, example_id="ex-a")
    example_b = _example_for(latent_b, example_id="ex-b")
    splits = {
        Split.TRAIN: [example_a],
        Split.TEST: [example_b],
        Split.CALIBRATION: [],
        Split.DEV: [],
        Split.HELDOUT_FAMILY: [],
        Split.ADVERSARIAL: [],
    }
    with pytest.raises(LeakageError):
        assert_no_leakage(splits)


def test_heldout_family_rows_all_land_in_heldout_family_and_nowhere_else() -> None:
    heldout_family_id = "fam-21"
    assert is_heldout_family(heldout_family_id)
    examples = [
        _example_for(
            make_latent(
                scenario_id=f"scenario-{i}",
                family_id=heldout_family_id,
                template_lineage=[f"{heldout_family_id}#scenario-{i}"],
            ),
            example_id=f"ex-{i}",
        )
        for i in range(20)
    ]
    splits = split_examples(examples)
    assert len(splits[Split.HELDOUT_FAMILY]) == 20
    for split, rows in splits.items():
        if split is not Split.HELDOUT_FAMILY:
            assert rows == []


def test_non_heldout_family_scenarios_spread_across_group_splits() -> None:
    non_heldout_family_id = "fam-0"
    assert not is_heldout_family(non_heldout_family_id)
    examples = [
        _example_for(
            make_latent(
                scenario_id=f"scenario-{i}",
                family_id=non_heldout_family_id,
                template_lineage=[f"{non_heldout_family_id}#scenario-{i}"],
            ),
            example_id=f"ex-{i}",
        )
        for i in range(200)
    ]
    splits = split_examples(examples)
    assert splits[Split.HELDOUT_FAMILY] == []
    occupied = {split for split, rows in splits.items() if rows}
    assert occupied == {Split.TRAIN, Split.CALIBRATION, Split.DEV, Split.TEST, Split.ADVERSARIAL}


def test_assert_no_leakage_raises_when_heldout_family_also_appears_elsewhere() -> None:
    heldout_family_id = "fam-21"
    latent_heldout = make_latent(scenario_id="a", family_id=heldout_family_id)
    latent_train = make_latent(scenario_id="b", family_id=heldout_family_id)
    example_heldout = _example_for(latent_heldout, example_id="ex-a")
    example_train = _example_for(latent_train, example_id="ex-b")
    splits = {
        Split.TRAIN: [example_train],
        Split.HELDOUT_FAMILY: [example_heldout],
        Split.CALIBRATION: [],
        Split.DEV: [],
        Split.TEST: [],
        Split.ADVERSARIAL: [],
    }
    with pytest.raises(LeakageError):
        assert_no_leakage(splits)


def test_contrastive_pair_still_lands_together_with_heldout_tier() -> None:
    base = make_latent(scenario_id="base-1", family_id="fam-21")
    flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
    pair_id = contrastive_pair_id(base.scenario_id, ContrastiveAxis.RESOURCE_SENSITIVITY)
    transformation = Transformation(
        axis=ContrastiveAxis.RESOURCE_SENSITIVITY,
        base_example_id="ex-base-1",
        from_value="internal",
        to_value="restricted",
    )
    examples = [
        _example_for(base, example_id="ex-base-1"),
        _example_for(
            flipped,
            example_id="ex-flip-1",
            family_id=base.family_id,
            contrastive_pair_id=pair_id,
            transformation=transformation,
        ),
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    found = [split for split, rows in splits.items() if rows]
    assert len(found) == 1


def _heldout_kind() -> PolicyPredicateKind:
    return next(iter(HELDOUT_POLICY_KINDS))


def test_heldout_policy_kind_examples_never_land_in_train_or_eval() -> None:
    kind = _heldout_kind()
    examples = [
        _example_for(
            make_latent(
                scenario_id=f"scenario-{i}",
                family_id=f"fam-kind-{i}",
                template_lineage=[f"fam-kind-{i}#scenario-{i}"],
                policy_supplied=True,
                policy_predicates=[PolicyPredicate(id="p", kind=kind)],
            ),
            example_id=f"ex-{i}",
        )
        for i in range(30)
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    assert len(splits[Split.HELDOUT_POLICY_KIND]) > 0
    assert len(splits[Split.HELDOUT_POLICY_KIND]) + len(splits[Split.HELDOUT_FAMILY]) == 30
    for split in (Split.TRAIN, Split.CALIBRATION, Split.DEV, Split.TEST):
        assert splits[split] == []


def test_heldout_policy_phrasing_examples_never_land_in_train_or_eval() -> None:
    kind = next(k for k in PolicyPredicateKind if k not in HELDOUT_POLICY_KINDS)
    paraphrase_index = next(iter(HELDOUT_PARAPHRASE_INDICES))
    examples = [
        _example_for(
            make_latent(
                scenario_id=f"scenario-{i}",
                family_id=f"fam-phrasing-{i}",
                template_lineage=[f"fam-phrasing-{i}#scenario-{i}"],
                policy_supplied=True,
                policy_predicates=[
                    PolicyPredicate(id="p", kind=kind, paraphrase_index=paraphrase_index)
                ],
            ),
            example_id=f"ex-{i}",
        )
        for i in range(30)
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    assert len(splits[Split.HELDOUT_POLICY_PHRASING]) > 0
    assert len(splits[Split.HELDOUT_POLICY_PHRASING]) + len(splits[Split.HELDOUT_FAMILY]) == 30
    for split in (Split.TRAIN, Split.CALIBRATION, Split.DEV, Split.TEST):
        assert splits[split] == []


def test_trained_kind_with_trained_paraphrase_can_reach_train() -> None:
    kind = next(k for k in PolicyPredicateKind if k not in HELDOUT_POLICY_KINDS)
    paraphrase_index = next(i for i in range(4) if i not in HELDOUT_PARAPHRASE_INDICES)
    examples = [
        _example_for(
            make_latent(
                scenario_id=f"scenario-{i}",
                family_id=f"fam-trained-{i}",
                template_lineage=[f"fam-trained-{i}#scenario-{i}"],
                policy_supplied=True,
                policy_predicates=[
                    PolicyPredicate(id="p", kind=kind, paraphrase_index=paraphrase_index)
                ],
            ),
            example_id=f"ex-{i}",
        )
        for i in range(200)
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    assert splits[Split.HELDOUT_POLICY_KIND] == []
    assert splits[Split.HELDOUT_POLICY_PHRASING] == []
    assert len(splits[Split.TRAIN]) > 0


def test_heldout_policy_kind_pair_lands_together() -> None:
    kind = _heldout_kind()
    base = make_latent(
        scenario_id="base-1",
        policy_supplied=True,
        policy_predicates=[PolicyPredicate(id="p", kind=kind)],
    )
    flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
    pair_id = contrastive_pair_id(base.scenario_id, ContrastiveAxis.RESOURCE_SENSITIVITY)
    transformation = Transformation(
        axis=ContrastiveAxis.RESOURCE_SENSITIVITY,
        base_example_id="ex-base-1",
        from_value="internal",
        to_value="restricted",
    )
    examples = [
        _example_for(base, example_id="ex-base-1"),
        _example_for(
            flipped,
            example_id="ex-flip-1",
            family_id=base.family_id,
            contrastive_pair_id=pair_id,
            transformation=transformation,
        ),
    ]
    splits = split_examples(examples)
    assert_no_leakage(splits)
    found = [split for split, rows in splits.items() if rows]
    assert found == [Split.HELDOUT_POLICY_KIND]
