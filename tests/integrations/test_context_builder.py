from __future__ import annotations

import warnings

import pytest

from forecheck.contracts import DestinationRelationship, Sensitivity, TrustLevel
from forecheck.integrations.context_builder import ActionContextBuilder, ForecheckContextWarning


def _base_builder() -> ActionContextBuilder:
    return (
        ActionContextBuilder()
        .objective("Read the quarterly report.", explicit=True)
        .principal("user-1")
        .propose("read_document", arguments={"doc_id": 1})
    )


def _build_and_collect_warnings(builder: ActionContextBuilder) -> list[str]:
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        builder.build()
    return [str(w.message) for w in record]


def test_build_raises_when_required_fields_missing() -> None:
    with pytest.raises(ValueError, match="objective"):
        ActionContextBuilder().build()


def test_build_reports_all_missing_required_fields() -> None:
    with pytest.raises(ValueError) as exc_info:
        ActionContextBuilder().objective("x").build()
    message = str(exc_info.value)
    assert "principal" in message
    assert "agent" in message
    assert "proposed_action" in message


def test_empty_delegated_scopes_warns() -> None:
    builder = _base_builder().agent("agent-1")
    with pytest.warns(ForecheckContextWarning, match="delegated_scopes"):
        builder.build()


def test_nonempty_delegated_scopes_does_not_warn_about_scopes() -> None:
    builder = _base_builder().agent("agent-1", delegated_scopes=["docs:read"])
    messages = _build_and_collect_warnings(builder)
    assert not any("delegated_scopes" in m for m in messages)


def test_unknown_observation_trust_warns() -> None:
    builder = (
        _base_builder()
        .agent("agent-1", delegated_scopes=["docs:read"])
        .observe("src", "content", trust=TrustLevel.UNKNOWN)
    )
    with pytest.warns(ForecheckContextWarning, match="UNKNOWN"):
        builder.build()


def test_default_observation_trust_is_untrusted_and_does_not_warn() -> None:
    builder = (
        _base_builder().agent("agent-1", delegated_scopes=["docs:read"]).observe("src", "content")
    )
    messages = _build_and_collect_warnings(builder)
    assert not any("observation has trust=UNKNOWN" in m for m in messages)


def test_default_sensitivity_resource_warns() -> None:
    builder = (
        _base_builder().agent("agent-1", delegated_scopes=["docs:read"]).resource("urn:file:1")
    )
    with pytest.warns(ForecheckContextWarning, match="sensitivity"):
        builder.build()


def test_explicit_nondefault_sensitivity_does_not_warn_about_sensitivity() -> None:
    builder = (
        _base_builder()
        .agent("agent-1", delegated_scopes=["docs:read"])
        .resource("urn:file:1", sensitivity=Sensitivity.CONFIDENTIAL)
    )
    messages = _build_and_collect_warnings(builder)
    assert not any("sensitivity" in m for m in messages)


def test_unknown_destination_trust_warns() -> None:
    builder = (
        _base_builder()
        .agent("agent-1", delegated_scopes=["docs:read"])
        .destination("external.example", relationship=DestinationRelationship.UNKNOWN_EXTERNAL)
    )
    with pytest.warns(ForecheckContextWarning, match="destination.trust"):
        builder.build()


def test_known_destination_trust_does_not_warn() -> None:
    builder = (
        _base_builder()
        .agent("agent-1", delegated_scopes=["docs:read"])
        .destination(
            "colleague@tenant.example",
            relationship=DestinationRelationship.SAME_TENANT,
            trust=TrustLevel.TRUSTED_TOOL,
        )
    )
    messages = _build_and_collect_warnings(builder)
    assert not any("destination.trust" in m for m in messages)


def test_step_computes_arguments_digest() -> None:
    builder = _base_builder().agent("agent-1", delegated_scopes=["docs:read"])
    builder = builder.step("search", arguments={"q": "hi"}, result_trust=TrustLevel.UNTRUSTED)
    context = builder.build()
    assert context.trajectory[0].arguments_digest is not None


def test_fully_specified_context_builds_without_warnings() -> None:
    builder = (
        _base_builder()
        .agent("agent-1", delegated_scopes=["docs:read"])
        .resource("urn:file:1", sensitivity=Sensitivity.CONFIDENTIAL)
        .destination(
            "colleague@tenant.example",
            relationship=DestinationRelationship.SAME_TENANT,
            trust=TrustLevel.TRUSTED_TOOL,
        )
    )
    messages = _build_and_collect_warnings(builder)
    assert not messages


def test_build_returns_expected_tool_name() -> None:
    context = _base_builder().agent("agent-1", delegated_scopes=["docs:read"]).build()
    assert context.proposed_action.tool_name == "read_document"
