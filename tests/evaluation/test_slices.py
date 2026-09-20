from __future__ import annotations

from conftest import make_example, make_paraphrase_pair

from forecheck.contracts import (
    ContextGap,
    DifficultyTier,
    Observation,
    RiskDimension,
    Split,
    ToolFamily,
    TrajectoryStep,
    TrustLevel,
)
from forecheck.evaluation.metrics import DimensionMetrics, ThresholdMetrics
from forecheck.evaluation.report import SliceReport
from forecheck.evaluation.slices import (
    context_gap_count_bucket,
    rendered_context_length,
    rendered_context_length_bucket,
    slice_is_benign_hard_negative,
    slice_policy_present_vs_absent,
    slices_by_context_gap_count,
    slices_by_difficulty,
    slices_by_out_of_domain_tool,
    slices_by_split,
    slices_by_tool_family,
    slices_by_trajectory_length_bucket,
    surface_paraphrase_slices,
    trajectory_length_bucket,
    worst_slice,
)


def _dm(dimension: RiskDimension, f1: float) -> DimensionMetrics:
    return DimensionMetrics(
        dimension=dimension,
        n_evaluable=10,
        n_positive=5,
        positive_rate=0.5,
        auprc=None,
        auroc=None,
        brier=None,
        nll=None,
        ece=None,
        adaptive_ece=None,
        reliability_bins=(),
        at_threshold=ThresholdMetrics(threshold=0.5, precision=f1, recall=f1, f1=f1),
        at_optimal_threshold=None,
        optimal_threshold=None,
    )


def test_trajectory_length_bucket_boundaries() -> None:
    assert trajectory_length_bucket(0) == "0"
    assert trajectory_length_bucket(1) == "1-3"
    assert trajectory_length_bucket(3) == "1-3"
    assert trajectory_length_bucket(4) == "4-10"
    assert trajectory_length_bucket(10) == "4-10"
    assert trajectory_length_bucket(11) == "11+"


def test_context_gap_count_bucket_boundaries() -> None:
    assert context_gap_count_bucket(0) == "0"
    assert context_gap_count_bucket(1) == "1"
    assert context_gap_count_bucket(2) == "2"
    assert context_gap_count_bucket(3) == "3+"
    assert context_gap_count_bucket(9) == "3+"


def test_slices_by_tool_family_partitions_examples() -> None:
    a = make_example("a", tool_family=ToolFamily.EMAIL_MESSAGING)
    b = make_example("b", tool_family=ToolFamily.CLOUD_ADMIN)
    slices = slices_by_tool_family([a, b])
    names = {s.name for s in slices}
    assert names == {"tool_family=email_messaging", "tool_family=cloud_admin"}
    for s in slices:
        if s.name == "tool_family=email_messaging":
            assert s.select([a, b]) == [0]
        else:
            assert s.select([a, b]) == [1]


def test_slices_by_difficulty() -> None:
    easy = make_example("e", difficulty=DifficultyTier.EASY)
    hard = make_example("h", difficulty=DifficultyTier.HARD)
    slices = slices_by_difficulty([easy, hard])
    by_name = {s.name: s for s in slices}
    assert by_name["difficulty=easy"].select([easy, hard]) == [0]
    assert by_name["difficulty=hard"].select([easy, hard]) == [1]


def test_slices_by_split() -> None:
    dev = make_example("d", split=Split.DEV)
    test = make_example("t", split=Split.TEST)
    slices = slices_by_split([dev, test])
    by_name = {s.name: s for s in slices}
    assert by_name["split=dev"].select([dev, test]) == [0]
    assert by_name["split=test"].select([dev, test]) == [1]


def test_slice_is_benign_hard_negative() -> None:
    benign = make_example("b", is_benign_hard_negative=True)
    other = make_example("o", is_benign_hard_negative=False)
    sl = slice_is_benign_hard_negative()
    assert sl.select([benign, other]) == [0]


def test_slices_by_trajectory_length_bucket() -> None:
    step = TrajectoryStep(index=0, tool_name="email.read_message", arguments={})
    none = make_example("n0", trajectory=())
    short = make_example("n1", trajectory=(step,))
    slices = slices_by_trajectory_length_bucket([none, short])
    by_name = {s.name: s for s in slices}
    assert by_name["trajectory_length=0"].select([none, short]) == [0]
    assert by_name["trajectory_length=1-3"].select([none, short]) == [1]


def test_slices_by_context_gap_count() -> None:
    zero = make_example("z", context_gaps=())
    two = make_example("t", context_gaps=(ContextGap.MISSING_POLICY, ContextGap.MISSING_OBJECTIVE))
    slices = slices_by_context_gap_count([zero, two])
    by_name = {s.name: s for s in slices}
    assert by_name["context_gaps=0"].select([zero, two]) == [0]
    assert by_name["context_gaps=2"].select([zero, two]) == [1]


def test_context_gap_none_is_not_counted() -> None:
    example = make_example("x", context_gaps=(ContextGap.NONE, ContextGap.MISSING_POLICY))
    slices = slices_by_context_gap_count([example])
    by_name = {s.name: s for s in slices}
    assert by_name["context_gaps=1"].select([example]) == [0]


def test_rendered_context_length_grows_with_observations() -> None:
    short_example = make_example("short")
    long_example = make_example(
        "long",
        observations=(
            Observation(
                id="obs-1",
                source="web",
                trust=TrustLevel.UNTRUSTED,
                content="x" * 5000,
            ),
        ),
    )
    assert rendered_context_length(long_example) > rendered_context_length(short_example)
    assert rendered_context_length_bucket(rendered_context_length(long_example)) in (
        "4k-16k",
        "16k+",
    )


def test_slice_policy_present_vs_absent() -> None:
    absent = make_example("a", policies=())
    from forecheck.contracts import PolicyStatement

    present = make_example(
        "p", policies=(PolicyStatement(id="p1", text="No external payments over $500."),)
    )
    present_slice, absent_slice = slice_policy_present_vs_absent()
    assert present_slice.select([absent, present]) == [1]
    assert absent_slice.select([absent, present]) == [0]


def test_slices_by_out_of_domain_tool() -> None:
    known = make_example("k", tool_name="email.send_message")
    unknown = make_example("u", tool_name="crypto.wire_transfer")
    sl = slices_by_out_of_domain_tool(frozenset({"email.send_message"}))
    assert sl.select([known, unknown]) == [1]


def test_surface_paraphrase_slice_matches_only_transformed_row() -> None:
    base, transformed = make_paraphrase_pair()
    sl = surface_paraphrase_slices([base, transformed])[0]
    assert sl.select([base, transformed]) == [1]


def test_worst_slice_picks_minimum_macro_value() -> None:
    dim = RiskDimension.FINANCIAL_COMMITMENT
    good = SliceReport(name="good", n=10, dimensions={dim: _dm(dim, 0.9)})
    bad = SliceReport(name="bad", n=10, dimensions={dim: _dm(dim, 0.1)})

    class _Report:
        def __init__(self) -> None:
            self.slices = [good, bad]

    result = worst_slice(_Report(), "f1")
    assert result is not None
    assert result[0] == "bad"
    assert result[1] == 0.1


def test_worst_slice_empty_returns_none() -> None:
    class _Report:
        def __init__(self) -> None:
            self.slices: list[SliceReport] = []

    assert worst_slice(_Report(), "f1") is None
