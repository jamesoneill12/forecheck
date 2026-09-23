from __future__ import annotations

from pathlib import Path

import pytest

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.data.io import read_jsonl, write_jsonl
from forecheck.external.agentdojo import (
    label_call,
    load_ground_truth,
    overlay_identity,
    parse_trace,
    to_example,
)
from forecheck.inference.serialization import render_context

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agentdojo"
GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "external" / "agentdojo" / "ground_truth.json"
)

NONE_TRACE = FIXTURES / "user_task_2_none.json"
INJECTION_SUCCEEDED = FIXTURES / "user_task_2_injection_task_0_security_true.json"
INJECTION_FAILED = FIXTURES / "user_task_5_injection_task_0_security_false.json"


@pytest.fixture(scope="module")
def ground_truth() -> dict:
    return load_ground_truth(GROUND_TRUTH_PATH)


def test_parse_trace_none_run() -> None:
    trace = parse_trace(NONE_TRACE)
    assert trace.suite_name == "banking"
    assert trace.user_task_id == "user_task_2"
    assert trace.injection_task_id is None
    assert trace.attack_type is None
    assert trace.principal_name == "Emma Johnson"
    assert len(trace.proposed_calls) > 0


def test_parse_trace_injection_run() -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    assert trace.injection_task_id == "injection_task_0"
    assert trace.attack_type is not None
    assert trace.security is True
    functions = [c.function for c in trace.proposed_calls]
    assert "send_money" in functions
    send_money_call = next(c for c in trace.proposed_calls if c.function == "send_money")
    assert send_money_call.prior_trajectory


def test_overlay_identity_entitlements_and_scope(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    overlay = overlay_identity("banking", trace, ground_truth)
    assert "send_money" in overlay.entitlements
    assert "update_password" in overlay.entitlements
    assert set(overlay.delegated_scopes) == {
        "read_file",
        "get_scheduled_transactions",
        "update_scheduled_transaction",
    }
    assert overlay.policy_ids


def test_label_call_attacker_send_money_is_influence_and_unauthorized(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    labels = label_call(call, trace, ground_truth)
    assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.YES
    assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.YES
    assert labels.values[RiskDimension.FINANCIAL_COMMITMENT] is LabelValue.YES


def test_label_call_user_ground_truth_call_is_not_influence_or_unauthorized(
    ground_truth: dict,
) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "read_file")
    labels = label_call(call, trace, ground_truth)
    assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO
    assert labels.values[RiskDimension.UNAUTHORIZED_SCOPE] is LabelValue.NO


def test_label_call_failed_injection_is_not_influence(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_FAILED)
    assert trace.security is False
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    labels = label_call(call, trace, ground_truth)
    assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO


def test_label_call_no_injection_task_is_not_applicable(ground_truth: dict) -> None:
    trace = parse_trace(NONE_TRACE)
    call = trace.proposed_calls[0]
    labels = label_call(call, trace, ground_truth)
    assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NOT_APPLICABLE


def test_label_call_all_dimensions_present(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = trace.proposed_calls[0]
    labels = label_call(call, trace, ground_truth)
    assert set(labels.values) == set(RiskDimension)
    for dimension in (
        RiskDimension.PRIVILEGE_ESCALATION,
        RiskDimension.INSUFFICIENT_CONTEXT,
        RiskDimension.SENSITIVE_DATA_EXPOSURE,
        RiskDimension.SUSPICIOUS_ACTION_SEQUENCE,
    ):
        assert labels.values[dimension] is LabelValue.NOT_APPLICABLE


def test_to_example_round_trips_and_renders(tmp_path: Path, ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    overlay = overlay_identity("banking", trace, ground_truth)
    examples = []
    for call in trace.proposed_calls:
        labels = label_call(call, trace, ground_truth)
        examples.append(to_example(call, trace, overlay, labels))

    out_path = tmp_path / "agentdojo.jsonl"
    write_jsonl(out_path, examples)
    read_back = read_jsonl(out_path)

    assert [e.example_id for e in read_back] == [e.example_id for e in examples]
    for example in read_back:
        text = render_context(example.context)
        assert example.context.proposed_action.tool_name in text
        assert example.license.usage.value == "eval_only"
        assert example.license.source_name == "agentdojo"


def test_label_call_placeholder_only_match_is_not_influence(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    benign = call.model_copy(
        update={"args": {**call.args, "recipient": "GB29NWBK60161331926819", "date": "2022-01-01"}}
    )
    labels = label_call(benign, trace, ground_truth)
    assert labels.values[RiskDimension.PROMPT_INJECTION_INFLUENCE] is LabelValue.NO


def test_to_example_puts_tool_results_in_untrusted_observations(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    overlay = overlay_identity("banking", trace, ground_truth)
    example = to_example(call, trace, overlay, label_call(call, trace, ground_truth))
    assert example.context.observations
    assert all(o.trust.value == "untrusted" for o in example.context.observations)
    assert any("<INFORMATION>" in o.content for o in example.context.observations)


def test_to_example_destination_trust_does_not_depend_on_label(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    overlay = overlay_identity("banking", trace, ground_truth)
    labels = label_call(call, trace, ground_truth)
    flipped = labels.model_copy(
        update={
            "values": {
                **labels.values,
                RiskDimension.PROMPT_INJECTION_INFLUENCE: LabelValue.NO,
            }
        }
    )
    a = to_example(call, trace, overlay, labels).context.destination
    b = to_example(call, trace, overlay, flipped).context.destination
    assert a is not None and b is not None
    assert (a.trust, a.relationship) == (b.trust, b.relationship)


def test_to_example_destination_from_args_even_when_label_not_applicable(
    ground_truth: dict,
) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    overlay = overlay_identity("banking", trace, ground_truth)
    labels = label_call(call, trace, ground_truth)
    na = labels.model_copy(
        update={
            "values": {
                **labels.values,
                RiskDimension.UNTRUSTED_DESTINATION: LabelValue.NOT_APPLICABLE,
            }
        }
    )
    example = to_example(call, trace, overlay, na)
    assert example.context.destination is not None
    assert example.latent.destination_present is True


def test_to_example_truncates_injected_destination_identifier(ground_truth: dict) -> None:
    trace = parse_trace(INJECTION_SUCCEEDED)
    call = next(c for c in trace.proposed_calls if c.function == "send_money")
    call = call.model_copy(update={"args": {**call.args, "recipient": "X" * 5000}})
    overlay = overlay_identity("banking", trace, ground_truth)
    labels = label_call(call, trace, ground_truth)
    example = to_example(call, trace, overlay, labels)
    assert example.context.destination is not None
    assert len(example.context.destination.identifier) == 200
