from __future__ import annotations

import random

from forecheck.contracts import ToolFamily
from forecheck.data.labeling import derive_labels
from forecheck.generation.scenarios import iter_scenarios, sample_scenario


def test_sample_scenario_is_deterministic_given_same_rng_state() -> None:
    a = sample_scenario(random.Random(7), ToolFamily.EMAIL_MESSAGING, "s-1")
    b = sample_scenario(random.Random(7), ToolFamily.EMAIL_MESSAGING, "s-1")
    assert a == b


def test_sample_scenario_stays_within_family() -> None:
    rng = random.Random(1)
    for _ in range(50):
        scenario = sample_scenario(rng, ToolFamily.PAYMENTS_PROCUREMENT, "s")
        assert scenario.tool.family is ToolFamily.PAYMENTS_PROCUREMENT


def test_sample_scenario_produces_valid_labels_for_every_family() -> None:
    rng = random.Random(3)
    for family in ToolFamily:
        for i in range(10):
            scenario = sample_scenario(rng, family, f"{family.value}-{i}")
            labels = derive_labels(scenario)
            assert len(labels.values) == len(labels.values)


def test_iter_scenarios_covers_all_families() -> None:
    scenarios = iter_scenarios(random.Random(5), n_per_family=5)
    families = {s.tool.family for s in scenarios}
    assert families == set(ToolFamily)
    assert len(scenarios) == 5 * len(ToolFamily)


def test_sampled_scenarios_include_a_healthy_share_of_benign_rows() -> None:
    rng = random.Random(11)
    scenarios = iter_scenarios(rng, n_per_family=60)
    all_clean = 0
    for scenario in scenarios:
        labels = derive_labels(scenario)
        if all(v.value in ("no", "not_applicable") for v in labels.values.values()):
            all_clean += 1
    assert all_clean / len(scenarios) >= 0.30
