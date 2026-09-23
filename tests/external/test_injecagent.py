from __future__ import annotations

from pathlib import Path

import pytest

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.data.io import read_jsonl, write_jsonl
from forecheck.external.injecagent import (
    fill_attacker_args,
    iter_examples,
    load_cases,
    load_simulated_responses,
    load_tools,
    overlay_identity,
    to_attacker_examples,
    to_benign_example,
)
from forecheck.inference.serialization import render_context

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "injecagent"


@pytest.fixture(scope="module")
def tools():
    return load_tools(FIXTURES / "tools.json")


@pytest.fixture(scope="module")
def sim_responses():
    return load_simulated_responses(FIXTURES / "attacker_simulated_responses.json")


@pytest.fixture(scope="module")
def dh_cases(tools):
    return load_cases(FIXTURES / "test_cases_dh_base.json", "dh")


@pytest.fixture(scope="module")
def ds_cases(tools):
    return load_cases(FIXTURES / "test_cases_ds_base.json", "ds")


def test_load_cases_counts(dh_cases, ds_cases) -> None:
    assert len(dh_cases) == 2
    assert len(ds_cases) == 2
    assert all(c.case_type == "dh" for c in dh_cases)
    assert all(len(c.attacker_tools) == 1 for c in dh_cases)
    assert all(c.case_type == "ds" for c in ds_cases)
    assert all(len(c.attacker_tools) == 2 for c in ds_cases)


def test_dh_case_yields_three_examples(dh_cases, tools, sim_responses) -> None:
    case = dh_cases[0]
    overlay = overlay_identity(case, tools)
    examples = [to_benign_example(case, tools, overlay)]
    examples += to_attacker_examples(case, tools, overlay, sim_responses)
    assert len(examples) == 3


def test_ds_case_yields_five_examples(ds_cases, tools, sim_responses) -> None:
    case = ds_cases[0]
    overlay = overlay_identity(case, tools)
    examples = [to_benign_example(case, tools, overlay)]
    examples += to_attacker_examples(case, tools, overlay, sim_responses)
    assert len(examples) == 5


def test_overlay_entitlements_include_user_and_attacker_toolkits(ds_cases, tools) -> None:
    case = ds_cases[0]
    overlay = overlay_identity(case, tools)
    assert "AmazonGetProductDetails" in overlay.entitlements
    assert "AmazonViewSavedAddresses" in overlay.entitlements
    assert "GmailSendEmail" in overlay.entitlements
    assert overlay.delegated_scopes == [case.user_tool]


def test_benign_example_labels(dh_cases, tools) -> None:
    case = dh_cases[0]
    overlay = overlay_identity(case, tools)
    example = to_benign_example(case, tools, overlay)
    labels = example.labels.values
    assert labels[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NOT_APPLICABLE
    assert labels[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.NO
    assert labels[RiskDimension.POLICY_CONFLICT] is LabelValue.NO
    assert not example.context.trajectory
    assert not example.context.observations


def test_attacker_example_labels(dh_cases, tools, sim_responses) -> None:
    case = dh_cases[0]
    overlay = overlay_identity(case, tools)
    poisoned, clean = to_attacker_examples(case, tools, overlay, sim_responses)
    assert poisoned.labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.YES
    assert clean.labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO
    for example in (poisoned, clean):
        assert example.labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.YES
        destructive = example.labels.values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION]
        assert destructive is LabelValue.YES
    assert (
        poisoned.labels.values[RiskDimension.POLICY_CONFLICT]
        == clean.labels.values[RiskDimension.POLICY_CONFLICT]
    )


def test_injected_text_present_in_poisoned_not_clean(dh_cases, tools, sim_responses) -> None:
    case = dh_cases[0]
    overlay = overlay_identity(case, tools)
    poisoned, clean = to_attacker_examples(case, tools, overlay, sim_responses)
    assert any(case.attacker_instruction in o.content for o in poisoned.context.observations)
    assert not any(case.attacker_instruction in o.content for o in clean.context.observations)


def test_sensitive_data_exposure_only_on_ds_exfil_step(ds_cases, tools, sim_responses) -> None:
    case = ds_cases[0]
    overlay = overlay_identity(case, tools)
    examples = to_attacker_examples(case, tools, overlay, sim_responses)
    by_tool = {
        e.context.proposed_action.tool_name: e for e in examples if e.tags[2] == "variant:poisoned"
    }
    assert (
        by_tool["AmazonViewSavedAddresses"].labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE]
        is LabelValue.NOT_APPLICABLE
    )
    assert (
        by_tool["GmailSendEmail"].labels.values[RiskDimension.SENSITIVE_DATA_EXPOSURE]
        is LabelValue.YES
    )


def test_destination_trust_does_not_depend_on_label(ds_cases, tools, sim_responses) -> None:
    case = ds_cases[0]
    overlay = overlay_identity(case, tools)
    examples = to_attacker_examples(case, tools, overlay, sim_responses)
    poisoned = next(
        e
        for e in examples
        if e.context.proposed_action.tool_name == "GmailSendEmail" and "variant:poisoned" in e.tags
    )
    flipped = poisoned.labels.model_copy(
        update={
            "values": {
                **poisoned.labels.values,
                RiskDimension.PROMPT_INJECTION_INFLUENCE: LabelValue.NO,
            }
        }
    )
    rebuilt = poisoned.model_copy(update={"labels": flipped})
    assert (poisoned.context.destination.trust, poisoned.context.destination.relationship) == (
        rebuilt.context.destination.trust,
        rebuilt.context.destination.relationship,
    )


def test_fill_attacker_args_is_deterministic(dh_cases, tools) -> None:
    case = dh_cases[0]
    tool = tools[case.attacker_tools[0]]
    first = fill_attacker_args(tool, case.attacker_instruction)
    second = fill_attacker_args(tool, case.attacker_instruction)
    assert first == second


def test_fill_attacker_args_extracts_parenthesised_identifier(dh_cases, tools) -> None:
    case = dh_cases[0]
    tool = tools[case.attacker_tools[0]]
    assert fill_attacker_args(tool, case.attacker_instruction) == {
        "guest_ids": ["guest_amy01"],
        "permanent": True,
    }


_FREE_TEXT_PARAM_KEYWORDS = (
    "message",
    "body",
    "note",
    "content",
    "description",
    "snippet",
    "reason",
)


def test_attacker_args_never_echo_instruction_verbatim(
    dh_cases, ds_cases, tools, sim_responses
) -> None:
    for case in dh_cases + ds_cases:
        overlay = overlay_identity(case, tools)
        for example in to_attacker_examples(case, tools, overlay, sim_responses):
            for key, value in example.context.proposed_action.arguments.items():
                if not isinstance(value, str):
                    continue
                assert value != case.attacker_instruction
                is_free_text = any(kw in key.lower() for kw in _FREE_TEXT_PARAM_KEYWORDS)
                if not is_free_text:
                    assert len(value) <= 160


def test_round_trip_and_render(tmp_path: Path, dh_cases, ds_cases, tools, sim_responses) -> None:
    examples = list(iter_examples(dh_cases + ds_cases, tools, sim_responses))
    out_path = tmp_path / "injecagent.jsonl"
    write_jsonl(out_path, examples)
    read_back = read_jsonl(out_path)

    assert [e.example_id for e in read_back] == [e.example_id for e in examples]
    for example in read_back:
        text = render_context(example.context)
        assert example.context.proposed_action.tool_name in text
        assert example.license.usage.value == "eval_only"
        assert example.license.source_name == "injecagent"
