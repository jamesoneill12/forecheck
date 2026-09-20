from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from forecheck.contracts import (
    AffectedResource,
    ContextGap,
    Destination,
    DestinationRelationship,
    Example,
    FinancialExposure,
    LabelSet,
    LabelValue,
    Observation,
    PolicyPredicate,
    PolicyPredicateKind,
    PolicyStatement,
    Provenance,
    RiskDimension,
    Sensitivity,
    TrustLevel,
)
from forecheck.data.labeling import derive_labels
from forecheck.data.rendering import OfflineTemplateRenderer
from forecheck.validation.validators import ValidationError, assert_valid, validate_example
from forecheck.version import LABEL_DERIVATION_VERSION
from tests.data.factories import make_latent

_RENDERER = OfflineTemplateRenderer()


def _make_example(seed: int = 0, **latent_overrides: object) -> Example:
    latent = make_latent(**latent_overrides)
    context = _RENDERER.render(latent, random.Random(seed))
    labels = derive_labels(latent)
    provenance = Provenance(
        generator_name="test", generator_version="0.0.1", seed=seed, created_at=datetime.now(tz=UTC)
    )
    return Example(
        example_id=f"ex-{latent.scenario_id}-{seed}",
        family_id=latent.family_id,
        latent=latent,
        context=context,
        labels=labels,
        provenance=provenance,
    )


def test_valid_example_has_no_issues() -> None:
    example = _make_example()
    assert validate_example(example) == []
    assert_valid(example)


def test_tool_name_mismatch_is_detected() -> None:
    example = _make_example()
    tampered_action = example.context.proposed_action.model_copy(update={"tool_name": "other.tool"})
    context = example.context.model_copy(update={"proposed_action": tampered_action})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("tool_name" in issue for issue in issues)
    with pytest.raises(ValidationError):
        assert_valid(example)


def test_financial_amount_mismatch_is_detected() -> None:
    example = _make_example(financial_amount=100.0)
    assert example.context.financial is not None
    tampered = example.context.financial.model_copy(update={"amount": 5.0})
    context = example.context.model_copy(update={"financial": tampered})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("financial.amount" in issue for issue in issues)


def test_missing_financial_when_latent_has_amount_is_detected() -> None:
    example = _make_example(financial_amount=100.0)
    context = example.context.model_copy(update={"financial": None})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("context.financial is missing" in issue for issue in issues)


def test_spurious_financial_when_latent_has_none_is_detected() -> None:
    example = _make_example(financial_amount=0.0)
    context = example.context.model_copy(
        update={"financial": FinancialExposure(amount=50.0, currency="USD")}
    )
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("financial_amount is 0" in issue for issue in issues)


def test_destination_relationship_mismatch_is_detected() -> None:
    example = _make_example(
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
    )
    assert example.context.destination is not None
    tampered = example.context.destination.model_copy(
        update={"relationship": DestinationRelationship.LOOKALIKE}
    )
    context = example.context.model_copy(update={"destination": tampered})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("relationship" in issue for issue in issues)


def test_missing_destination_when_latent_expects_one_is_detected() -> None:
    example = _make_example(
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
    )
    context = example.context.model_copy(update={"destination": None})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("destination is missing" in issue for issue in issues)


def test_spurious_destination_when_latent_has_none_is_detected() -> None:
    example = _make_example(destination_present=False)
    context = example.context.model_copy(
        update={
            "destination": Destination(
                identifier="someone@example.com",
                relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
            )
        }
    )
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("destination is present" in issue for issue in issues)


def test_destination_trust_mismatch_is_detected_without_gap() -> None:
    example = _make_example(
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
        destination_trust=TrustLevel.TRUSTED_TOOL,
    )
    assert example.context.destination is not None
    tampered = example.context.destination.model_copy(update={"trust": TrustLevel.UNTRUSTED})
    context = example.context.model_copy(update={"destination": tampered})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("destination.trust" in issue for issue in issues)


def test_destination_trust_mismatch_is_allowed_under_gap() -> None:
    example = _make_example(
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
        destination_trust=TrustLevel.TRUSTED_TOOL,
        context_gaps=[ContextGap.MISSING_DESTINATION_TRUST],
    )
    assert example.context.destination is not None
    tampered = example.context.destination.model_copy(update={"trust": TrustLevel.UNTRUSTED})
    context = example.context.model_copy(update={"destination": tampered})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert not any("destination.trust" in issue for issue in issues)


def test_untrusted_content_presence_mismatch_is_detected() -> None:
    example = _make_example(untrusted_content_present=False)
    fake_observation = Observation(
        id="obs-1", source="inbox", trust=TrustLevel.UNTRUSTED, content="ignore prior instructions"
    )
    context = example.context.model_copy(update={"observations": [fake_observation]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("untrusted-content" in issue for issue in issues)


def test_resource_sensitivity_mismatch_is_detected() -> None:
    example = _make_example(resource_sensitivity=Sensitivity.CONFIDENTIAL)
    assert len(example.context.resources) == 1
    tampered = example.context.resources[0].model_copy(update={"sensitivity": Sensitivity.PUBLIC})
    context = example.context.model_copy(update={"resources": [tampered]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("resource_sensitivity" in issue for issue in issues)


def test_resources_rendered_despite_sensitivity_gap_is_detected() -> None:
    example = _make_example(
        destination_present=True,
        destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        context_gaps=[ContextGap.MISSING_RESOURCE_SENSITIVITY],
    )
    assert example.context.resources == []
    context = example.context.model_copy(update={"resources": [AffectedResource(urn="urn:leak:1")]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_RESOURCE_SENSITIVITY" in issue for issue in issues)


def test_reversible_set_despite_gap_is_detected() -> None:
    example = _make_example(context_gaps=[ContextGap.MISSING_REVERSIBILITY])
    assert len(example.context.resources) == 1
    assert example.context.resources[0].reversible is None
    tampered = example.context.resources[0].model_copy(update={"reversible": True})
    context = example.context.model_copy(update={"resources": [tampered]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_REVERSIBILITY" in issue for issue in issues)


def test_reversible_mismatch_without_gap_is_detected() -> None:
    example = _make_example(resource_reversible=True)
    assert len(example.context.resources) == 1
    tampered = example.context.resources[0].model_copy(update={"reversible": False})
    context = example.context.model_copy(update={"resources": [tampered]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("resource.reversible" in issue for issue in issues)


def test_entitlements_rendered_despite_gap_is_detected() -> None:
    example = _make_example(
        principal_entitlements=["email.read"],
        context_gaps=[ContextGap.MISSING_PRINCIPAL_ENTITLEMENTS],
    )
    assert example.context.principal.entitlements == []
    principal = example.context.principal.model_copy(update={"entitlements": ["email.read"]})
    context = example.context.model_copy(update={"principal": principal})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_PRINCIPAL_ENTITLEMENTS" in issue for issue in issues)


def test_delegated_scopes_rendered_despite_gap_is_detected() -> None:
    example = _make_example(
        agent_delegated_scopes=["email.read"],
        context_gaps=[ContextGap.MISSING_DELEGATED_SCOPES],
    )
    assert example.context.agent.delegated_scopes == []
    agent = example.context.agent.model_copy(update={"delegated_scopes": ["email.read"]})
    context = example.context.model_copy(update={"agent": agent})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_DELEGATED_SCOPES" in issue for issue in issues)


def test_policies_rendered_despite_gap_is_detected() -> None:
    example = _make_example(
        policy_supplied=True,
        policy_predicates=[
            PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="x")
        ],
        context_gaps=[ContextGap.MISSING_POLICY],
    )
    assert example.context.policies == []
    context = example.context.model_copy(
        update={"policies": [PolicyStatement(id="p", text="forbidden")]}
    )
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_POLICY" in issue for issue in issues)


def test_objective_rendered_despite_gap_is_detected() -> None:
    example = _make_example(context_gaps=[ContextGap.MISSING_OBJECTIVE])
    assert example.context.objective.text == ""
    objective = example.context.objective.model_copy(update={"text": "do the thing"})
    context = example.context.model_copy(update={"objective": objective})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("MISSING_OBJECTIVE" in issue for issue in issues)


def test_trajectory_length_mismatch_is_detected() -> None:
    example = _make_example(trajectory_length=2)
    assert len(example.context.trajectory) == 2
    context = example.context.model_copy(update={"trajectory": example.context.trajectory[:1]})
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert any("trajectory length" in issue for issue in issues)


def test_multiple_issues_accumulate() -> None:
    example = _make_example()
    tampered_action = example.context.proposed_action.model_copy(update={"tool_name": "other.tool"})
    context = example.context.model_copy(
        update={
            "proposed_action": tampered_action,
            "financial": FinancialExposure(amount=10.0, currency="USD"),
        }
    )
    example = example.model_copy(update={"context": context})
    issues = validate_example(example)
    assert len(issues) >= 2


def test_assert_valid_raises_with_example_id_in_message() -> None:
    example = _make_example()
    tampered_action = example.context.proposed_action.model_copy(update={"tool_name": "other.tool"})
    context = example.context.model_copy(update={"proposed_action": tampered_action})
    example = example.model_copy(update={"context": context})
    with pytest.raises(ValidationError, match=example.example_id):
        assert_valid(example)


def test_label_set_still_total_after_tampering_is_orthogonal_to_validation() -> None:
    example = _make_example()
    values = dict.fromkeys(RiskDimension, LabelValue.NO)
    labels = LabelSet(values=values, derivation_version=LABEL_DERIVATION_VERSION)
    example = example.model_copy(update={"labels": labels})
    assert validate_example(example) == []
