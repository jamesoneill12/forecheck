from __future__ import annotations

from forecheck.contracts import (
    INVARIANT_AXES,
    ActionOrigin,
    AuthorizationBasis,
    ContrastiveAxis,
    DestinationRelationship,
    OperationKind,
    PolicyPredicate,
    PolicyPredicateKind,
    Stage,
)
from forecheck.data.contrastive import AXIS_FLIPPERS, contrastive_pair_id, make_pair
from forecheck.data.labeling import derive_labels
from forecheck.data.tools import get_tool
from tests.data.factories import make_latent


def test_every_axis_has_a_registered_flipper() -> None:
    assert set(AXIS_FLIPPERS) == set(ContrastiveAxis)


def _bases_by_axis() -> dict[ContrastiveAxis, object]:
    grant_tool = get_tool("cloud.grant_iam_policy")
    return {
        ContrastiveAxis.PRINCIPAL_AUTHORIZATION: make_latent(
            required_scopes=["email.read"],
            principal_entitlements=["email.read"],
            agent_delegated_scopes=["email.read"],
        ),
        ContrastiveAxis.DESTINATION_TENANCY: make_latent(
            tool=get_tool("email.send_message"),
            operation=OperationKind.CREATE,
            destination_present=True,
            destination_relationship=DestinationRelationship.SAME_TENANT,
        ),
        ContrastiveAxis.RESOURCE_SENSITIVITY: make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        ),
        ContrastiveAxis.ENVIRONMENT_STAGE: make_latent(
            stage=Stage.PRODUCTION,
            policy_supplied=True,
            policy_predicates=[
                PolicyPredicate(
                    id="p", kind=PolicyPredicateKind.FORBID_IN_STAGE, stage=Stage.DEVELOPMENT
                )
            ],
        ),
        ContrastiveAxis.REVERSIBILITY: make_latent(resource_reversible=True),
        ContrastiveAxis.READ_VERSUS_WRITE: make_latent(operation=OperationKind.READ),
        ContrastiveAxis.FINANCIAL_MATERIALITY: make_latent(financial_amount=0.0),
        ContrastiveAxis.EXPLICIT_VERSUS_INFERRED_INTENT: make_latent(
            authorization_basis=AuthorizationBasis.EXPLICIT,
            policy_supplied=True,
            policy_predicates=[
                PolicyPredicate(id="p", kind=PolicyPredicateKind.REQUIRE_EXPLICIT_AUTHORIZATION)
            ],
        ),
        ContrastiveAxis.INSTRUCTION_PROVENANCE: make_latent(
            action_origin=ActionOrigin.PRINCIPAL_REQUEST,
            untrusted_content_present=True,
            untrusted_content_contains_instruction=True,
        ),
        ContrastiveAxis.PERMISSION_VERSUS_ESCALATION: make_latent(
            tool=grant_tool,
            operation=OperationKind.GRANT,
            principal_entitlements=["iam.read"],
            agent_delegated_scopes=["iam.read"],
            authority_before=["iam.read"],
            authority_after=["iam.read"],
        ),
        ContrastiveAxis.ISOLATED_VERSUS_SEQUENCE: make_latent(trajectory_length=0),
        ContrastiveAxis.KNOWN_VERSUS_LOOKALIKE_DESTINATION: make_latent(
            destination_present=True,
            destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
        ),
        ContrastiveAxis.POLICY_PRESENT_VERSUS_ABSENT: make_latent(
            policy_supplied=True,
            policy_predicates=[
                PolicyPredicate(
                    id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="email.read_message"
                )
            ],
        ),
        ContrastiveAxis.SURFACE_PARAPHRASE: make_latent(),
    }


def test_non_invariant_axes_change_the_label_set() -> None:
    bases = _bases_by_axis()
    for axis in ContrastiveAxis:
        if axis in INVARIANT_AXES:
            continue
        base = bases[axis]
        flipped = make_pair(base, axis)
        base_labels = derive_labels(base)
        flipped_labels = derive_labels(flipped)
        assert base_labels.values != flipped_labels.values, f"{axis} did not change labels"


def test_surface_paraphrase_is_label_invariant() -> None:
    base = _bases_by_axis()[ContrastiveAxis.SURFACE_PARAPHRASE]
    flipped = make_pair(base, ContrastiveAxis.SURFACE_PARAPHRASE)
    assert derive_labels(base).values == derive_labels(flipped).values


def test_pair_preserves_family_and_lineage() -> None:
    base = make_latent()
    flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
    assert flipped.family_id == base.family_id
    assert flipped.template_lineage == base.template_lineage


def test_pair_has_a_different_scenario_id() -> None:
    base = make_latent()
    flipped = make_pair(base, ContrastiveAxis.RESOURCE_SENSITIVITY)
    assert flipped.scenario_id != base.scenario_id


def test_contrastive_pair_id_is_deterministic() -> None:
    id_a = contrastive_pair_id("scenario-1", ContrastiveAxis.RESOURCE_SENSITIVITY)
    id_b = contrastive_pair_id("scenario-1", ContrastiveAxis.RESOURCE_SENSITIVITY)
    id_c = contrastive_pair_id("scenario-2", ContrastiveAxis.RESOURCE_SENSITIVITY)
    assert id_a == id_b
    assert id_a != id_c
