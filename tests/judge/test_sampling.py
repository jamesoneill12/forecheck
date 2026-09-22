from __future__ import annotations

from forecheck.contracts import LabelValue, PolicyPredicateKind, RiskDimension, ToolFamily
from forecheck.judge.sampling import render_coverage_table, stratified_sample
from tests.evaluation.conftest import all_no_labels
from tests.judge.conftest import make_judge_example

DIM = RiskDimension.FINANCIAL_COMMITMENT


def _pool_with_scarce_and_abundant_cells(n_abundant: int = 100, n_scarce: int = 5) -> list:
    pool = []
    for i in range(n_abundant):
        pool.append(
            make_judge_example(
                f"abundant-no-{i}", labels=all_no_labels(), tool_family=ToolFamily.EMAIL_MESSAGING
            )
        )
    for i in range(n_scarce):
        pool.append(
            make_judge_example(
                f"scarce-yes-{i}",
                labels=all_no_labels(**{DIM.value: LabelValue.YES}),
                tool_family=ToolFamily.CLOUD_ADMIN,
            )
        )
    return pool


def test_every_cell_reaches_target_when_enough_examples_are_available() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=200, n_scarce=30)
    result = stratified_sample(pool, n=100, seed=0, cell_target=20)

    yes_cell = result.coverage["cells"][f"{DIM.value}:yes"]
    no_cell = result.coverage["cells"][f"{DIM.value}:no"]
    assert yes_cell["selected"] >= 20
    assert no_cell["selected"] >= 20


def test_scarce_cell_takes_everything_available_when_below_target() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=200, n_scarce=5)
    result = stratified_sample(pool, n=100, seed=0, cell_target=20)

    yes_cell = result.coverage["cells"][f"{DIM.value}:yes"]
    assert yes_cell["available"] == 5
    assert yes_cell["target"] == 5
    assert yes_cell["selected"] == 5


def test_sample_never_exceeds_requested_n_or_pool_size() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=10, n_scarce=2)
    result = stratified_sample(pool, n=1000, seed=0, cell_target=20)
    assert result.coverage["n_selected"] == len(pool)
    assert len(result.rows) == len(pool)


def test_tool_family_coverage_is_spread_across_families() -> None:
    pool = []
    for i in range(50):
        pool.append(make_judge_example(f"email-{i}", tool_family=ToolFamily.EMAIL_MESSAGING))
    for i in range(5):
        pool.append(make_judge_example(f"cloud-{i}", tool_family=ToolFamily.CLOUD_ADMIN))

    result = stratified_sample(pool, n=20, seed=1, cell_target=20)

    families = result.coverage["tool_families"]
    assert families.get("cloud_admin", 0) >= 3
    assert families.get("email_messaging", 0) >= 1


def test_policy_kind_coverage_prefers_underrepresented_kinds() -> None:
    pool = []
    for i in range(50):
        pool.append(
            make_judge_example(f"common-{i}", policy_kinds=[PolicyPredicateKind.FORBID_TOOL])
        )
    for i in range(5):
        pool.append(
            make_judge_example(f"rare-{i}", policy_kinds=[PolicyPredicateKind.FORBID_CURRENCY])
        )

    result = stratified_sample(pool, n=20, seed=2, cell_target=20)

    kinds = result.coverage["policy_kinds"]
    assert kinds.get("forbid_currency", 0) >= 3


def test_sampling_is_deterministic_for_a_fixed_seed() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=40, n_scarce=10)
    first = stratified_sample(pool, n=15, seed=42, cell_target=5)
    second = stratified_sample(pool, n=15, seed=42, cell_target=5)
    assert [r.example_id for r in first.rows] == [r.example_id for r in second.rows]


def test_sample_rows_carry_full_and_stripped_renderings_and_generator_labels() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=5, n_scarce=2)
    result = stratified_sample(pool, n=3, seed=0, cell_target=1)
    for row in result.rows:
        assert row.rendered_full
        assert row.rendered_stripped
        assert row.rendered_full != row.rendered_stripped
        assert len(row.generator_labels) == len(RiskDimension)


def test_render_coverage_table_mentions_selected_and_pool_sizes() -> None:
    pool = _pool_with_scarce_and_abundant_cells(n_abundant=5, n_scarce=2)
    result = stratified_sample(pool, n=3, seed=0, cell_target=1)
    table = render_coverage_table(result.coverage)
    assert "selected 3 / pool 7" in table
