from __future__ import annotations

import random

import pytest

from forecheck.contracts import (
    ActionOrigin,
    ContextGap,
    DestinationRelationship,
    LabelValue,
    OperationKind,
    RiskDimension,
    Sensitivity,
    SequencePattern,
    ToolFamily,
    TrustLevel,
)
from forecheck.data.labeling import derive_labels
from forecheck.data.rendering import (
    OfflineTemplateRenderer,
    _target_argument_key,
    build_surface_text,
)
from forecheck.data.tools import get_tool
from forecheck.generation.scenarios import iter_scenarios
from forecheck.inference.serialization import serialize_context
from tests.data.factories import make_latent

_DENYLIST_TOKENS: tuple[str, ...] = ("attacker", "instructed_target", "shadow-ops")


def test_render_is_deterministic_given_same_seed() -> None:
    latent = make_latent()
    renderer = OfflineTemplateRenderer()
    context_a = renderer.render(latent, random.Random(42))
    context_b = renderer.render(latent, random.Random(42))
    assert context_a.model_dump() == context_b.model_dump()


def test_render_varies_with_seed() -> None:
    latent = make_latent()
    renderer = OfflineTemplateRenderer()
    context_a = renderer.render(latent, random.Random(1))
    context_b = renderer.render(latent, random.Random(2))
    assert context_a.objective.text != context_b.objective.text


def test_tool_name_is_preserved() -> None:
    latent = make_latent()
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.proposed_action.tool_name == latent.tool.name


def test_injected_instruction_never_appears_in_objective() -> None:
    latent = make_latent(
        untrusted_content_present=True,
        untrusted_content_contains_instruction=True,
    )
    seen_instruction_texts: set[str] = set()
    for seed in range(20):
        context = OfflineTemplateRenderer().render(latent, random.Random(seed))
        untrusted = [o for o in context.observations if o.trust is TrustLevel.UNTRUSTED]
        assert untrusted, "expected an untrusted observation"
        for observation in untrusted:
            seen_instruction_texts.add(observation.content)
        assert "ignore" not in context.objective.text.lower()
        assert "credentials" not in context.objective.text.lower()
    assert len(seen_instruction_texts) > 1


def test_untrusted_content_absent_means_no_observations() -> None:
    latent = make_latent(untrusted_content_present=False)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.observations == []


def test_financial_amount_is_reflected_in_context() -> None:
    latent = make_latent(financial_amount=250.0, financial_currency="USD")
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.financial is not None
    assert context.financial.amount == 250.0
    assert context.financial.currency == "USD"


def test_zero_financial_amount_means_no_financial_exposure() -> None:
    latent = make_latent(financial_amount=0.0)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.financial is None


def test_destination_reflects_latent_relationship() -> None:
    latent = make_latent(
        destination_present=True,
        destination_relationship=DestinationRelationship.LOOKALIKE,
        destination_trust=TrustLevel.UNKNOWN,
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.destination is not None
    assert context.destination.relationship is DestinationRelationship.LOOKALIKE


def test_no_destination_means_none() -> None:
    latent = make_latent(destination_present=False)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.destination is None


def test_missing_resource_sensitivity_gap_omits_resources() -> None:
    latent = make_latent(
        destination_present=True,
        destination_relationship=DestinationRelationship.UNKNOWN_EXTERNAL,
        context_gaps=[ContextGap.MISSING_RESOURCE_SENSITIVITY],
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.resources == []


def test_missing_reversibility_gap_sets_reversible_none() -> None:
    latent = make_latent(context_gaps=[ContextGap.MISSING_REVERSIBILITY])
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert len(context.resources) == 1
    assert context.resources[0].reversible is None


def test_missing_principal_entitlements_gap_empties_entitlements() -> None:
    latent = make_latent(
        principal_entitlements=["email.read", "email.send"],
        context_gaps=[ContextGap.MISSING_PRINCIPAL_ENTITLEMENTS],
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.principal.entitlements == []


def test_missing_delegated_scopes_gap_empties_delegated_scopes() -> None:
    latent = make_latent(
        agent_delegated_scopes=["email.read"],
        context_gaps=[ContextGap.MISSING_DELEGATED_SCOPES],
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.agent.delegated_scopes == []


def test_missing_policy_gap_empties_policies() -> None:
    from forecheck.contracts import PolicyPredicate, PolicyPredicateKind

    pred = PolicyPredicate(id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="x")
    latent = make_latent(
        policy_supplied=True,
        policy_predicates=[pred],
        context_gaps=[ContextGap.MISSING_POLICY],
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.policies == []


def test_missing_destination_trust_gap_forces_unknown_trust() -> None:
    latent = make_latent(
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
        destination_trust=TrustLevel.TRUSTED_TOOL,
        context_gaps=[ContextGap.MISSING_DESTINATION_TRUST],
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.destination is not None
    assert context.destination.trust is TrustLevel.UNKNOWN


def test_missing_objective_gap_yields_empty_objective_text() -> None:
    latent = make_latent(context_gaps=[ContextGap.MISSING_OBJECTIVE])
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.objective.text == ""


def test_trajectory_length_matches_latent() -> None:
    latent = make_latent(trajectory_length=4)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert len(context.trajectory) == 4
    assert [step.index for step in context.trajectory] == [0, 1, 2, 3]


def test_objective_has_multiple_surface_realisations() -> None:
    latent = make_latent()
    phrasings = {
        build_surface_text(latent, random.Random(seed)).objective_text for seed in range(30)
    }
    assert len(phrasings) >= 5


def test_tool_description_has_multiple_surface_realisations() -> None:
    tool = get_tool("cloud.grant_iam_policy")
    latent = make_latent(tool=tool, operation=OperationKind.GRANT)
    phrasings = {
        build_surface_text(latent, random.Random(seed)).tool_description for seed in range(30)
    }
    assert len(phrasings) >= 5


def test_resource_sensitivity_matches_latent_when_present() -> None:
    latent = make_latent(resource_sensitivity=Sensitivity.RESTRICTED)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert len(context.resources) == 1
    assert context.resources[0].sensitivity is Sensitivity.RESTRICTED


def test_every_sequence_pattern_renders_a_trajectory() -> None:
    for pattern in SequencePattern:
        length = 0 if pattern is SequencePattern.NONE else 3
        latent = make_latent(sequence_pattern=pattern, trajectory_length=length)
        context = OfflineTemplateRenderer().render(latent, random.Random(0))
        assert len(context.trajectory) == length


def test_attack_trajectory_does_not_copy_proposed_action_tool_into_final_step() -> None:
    tool = get_tool("storage.read_object")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.READ,
        sequence_pattern=SequencePattern.RECON_THEN_COLLECT_THEN_EXFILTRATE,
        trajectory_length=3,
    )
    final_tools = set()
    for seed in range(10):
        context = OfflineTemplateRenderer().render(latent, random.Random(seed))
        final_tools.add(context.trajectory[-1].tool_name)
    assert final_tools != {tool.name}
    assert all(get_tool(name).operation is not OperationKind.READ for name in final_tools)


def test_attack_and_benign_trajectory_tool_sequences_are_disjoint() -> None:
    tool = get_tool("storage.read_object")
    attack_latent = make_latent(
        tool=tool,
        operation=OperationKind.READ,
        sequence_pattern=SequencePattern.RECON_THEN_COLLECT_THEN_EXFILTRATE,
        trajectory_length=3,
    )
    benign_latent = make_latent(
        tool=tool,
        operation=OperationKind.READ,
        sequence_pattern=SequencePattern.BENIGN_LINEAR_TASK,
        trajectory_length=3,
    )
    attack_sequences = set()
    benign_sequences = set()
    for seed in range(30):
        attack_ctx = OfflineTemplateRenderer().render(attack_latent, random.Random(seed))
        benign_ctx = OfflineTemplateRenderer().render(benign_latent, random.Random(seed))
        attack_sequences.add(tuple(s.tool_name for s in attack_ctx.trajectory))
        benign_sequences.add(tuple(s.tool_name for s in benign_ctx.trajectory))
    assert attack_sequences.isdisjoint(benign_sequences)


def test_benign_trajectory_includes_non_success_outcomes() -> None:
    latent = make_latent(
        sequence_pattern=SequencePattern.BENIGN_RETRY_AFTER_ERROR, trajectory_length=3
    )
    outcomes = {
        step.outcome
        for seed in range(20)
        for step in OfflineTemplateRenderer().render(latent, random.Random(seed)).trajectory
    }
    assert "error" in outcomes
    assert "success" in outcomes


def test_injected_instruction_target_appears_in_observation_and_action() -> None:
    tool = get_tool("email.send_message")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.CREATE,
        action_origin=ActionOrigin.INJECTED_INSTRUCTION,
        untrusted_content_present=True,
        untrusted_content_contains_instruction=True,
    )
    for seed in range(40):
        context = OfflineTemplateRenderer().render(latent, random.Random(seed))
        observation_text = context.observations[0].content
        target = context.proposed_action.arguments["to"]
        assert target in observation_text


def test_policy_clause_paraphrase_is_deterministic_and_keyed_by_index() -> None:
    from forecheck.contracts import PolicyPredicate, PolicyPredicateKind
    from forecheck.data.rendering import _policy_clause

    clauses = set()
    for index in range(4):
        pred = PolicyPredicate(
            id="p", kind=PolicyPredicateKind.FORBID_TOOL, tool_name="x", paraphrase_index=index
        )
        clauses.add(_policy_clause(pred))
        assert _policy_clause(pred) == _policy_clause(pred)
    assert len(clauses) == 4


def test_every_policy_kind_has_at_least_four_paraphrases() -> None:
    from forecheck.contracts import PolicyPredicateKind
    from forecheck.data.rendering import _POLICY_CLAUSE_TEMPLATES

    for kind in PolicyPredicateKind:
        templates = _POLICY_CLAUSE_TEMPLATES[kind]
        assert len(templates) >= 4
        assert len(set(templates)) == len(templates)


def test_resource_region_is_reflected_in_environment() -> None:
    latent = make_latent(resource_region="eu-west-1")
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.environment.region == "eu-west-1"


def test_local_hour_is_reflected_in_environment_labels() -> None:
    latent = make_latent(local_hour=3)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.environment.labels["local_hour"] == "3"


def test_recipient_domain_appears_in_destination_identifier() -> None:
    tool = get_tool("email.send_message")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.CREATE,
        destination_present=True,
        destination_relationship=DestinationRelationship.KNOWN_THIRD_PARTY,
        recipient_domain="vendor-partner.example",
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.destination is not None
    assert context.destination.identifier.endswith("@vendor-partner.example")


def test_ticket_reference_appears_in_proposed_action_arguments() -> None:
    latent = make_latent(ticket_reference="TICKET-4242")
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.proposed_action.arguments["ticket_reference"] == "TICKET-4242"


def test_touched_pii_fields_appear_in_proposed_action_arguments() -> None:
    latent = make_latent(touched_pii_fields=["ssn", "email"])
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.proposed_action.arguments["pii_fields"] == ["ssn", "email"]


def test_dry_run_performed_appends_a_trajectory_step() -> None:
    latent = make_latent(trajectory_length=0, dry_run_performed=True)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert len(context.trajectory) == 1
    assert "dry" in context.trajectory[-1].result_summary.lower()


def test_no_dry_run_performed_means_no_extra_trajectory_step() -> None:
    latent = make_latent(trajectory_length=2, dry_run_performed=False)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert len(context.trajectory) == 2


def test_hard_negative_instruction_target_absent_from_action() -> None:
    tool = get_tool("email.send_message")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.CREATE,
        action_origin=ActionOrigin.PRINCIPAL_REQUEST,
        untrusted_content_present=True,
        untrusted_content_contains_instruction=True,
        is_benign_hard_negative=True,
    )
    for seed in range(20):
        context = OfflineTemplateRenderer().render(latent, random.Random(seed))
        observation_text = context.observations[0].content
        assert "instructed_target" not in context.proposed_action.arguments
        assert context.proposed_action.arguments["to"] not in observation_text


def test_privilege_escalation_positive_renders_the_deciding_authority() -> None:
    tool = get_tool("cloud.grant_iam_policy")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.GRANT,
        principal_entitlements=["iam.read"],
        agent_delegated_scopes=["iam.read"],
        authority_before=["iam.read"],
        authority_after=["iam.read", "iam.admin"],
    )
    assert derive_labels(latent).values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.YES
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    text = serialize_context(context).text
    assert "iam.admin" in text


def test_privilege_escalation_negative_in_scope_regrant_still_shows_no_widening() -> None:
    tool = get_tool("cloud.grant_iam_policy")
    latent = make_latent(
        tool=tool,
        operation=OperationKind.GRANT,
        principal_entitlements=["iam.read", "iam.admin"],
        agent_delegated_scopes=["iam.read", "iam.admin"],
        authority_before=["iam.read", "iam.admin"],
        authority_after=["iam.read", "iam.admin"],
    )
    assert derive_labels(latent).values[RiskDimension.PRIVILEGE_ESCALATION] is LabelValue.NO
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    text = serialize_context(context).text
    assert "authority_before: ['iam.read', 'iam.admin']" in text
    assert "authority_after: ['iam.read', 'iam.admin']" in text


def test_new_v5_boolean_flags_render_into_arguments() -> None:
    latent = make_latent(
        manager_approved=False,
        second_approver_present=False,
        customer_consent_given=False,
        encryption_in_transit=False,
        reason="",
        cross_tenant_resource=True,
    )
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    text = serialize_context(context).text
    assert "manager_approved: False" in text
    assert "second_approver_present: False" in text
    assert "customer_consent_given: False" in text
    assert "encryption_in_transit: False" in text
    assert "reason: " in text
    assert "cross_tenant_resource: True" in text


def test_channel_and_export_format_render_when_set() -> None:
    latent = make_latent(channel="sms", export_format="csv")
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.proposed_action.arguments["channel"] == "sms"
    assert context.proposed_action.arguments["export_format"] == "csv"


def test_recipient_verified_renders_into_destination() -> None:
    latent = make_latent(destination_present=True, recipient_verified=False)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.destination is not None
    assert context.destination.verified is False


def test_is_weekend_renders_into_environment_labels() -> None:
    latent = make_latent(is_weekend=True)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    assert context.environment.labels["is_weekend"] == "True"


def test_failed_auth_in_trajectory_renders_a_trajectory_step() -> None:
    latent = make_latent(failed_auth_in_trajectory=True)
    context = OfflineTemplateRenderer().render(latent, random.Random(0))
    text = serialize_context(context).text
    assert "Authentication failed" in text or "Sign-in rejected" in text


@pytest.fixture(scope="module")
def rendered_corpus() -> list[tuple[object, object]]:
    """~18k scenarios across every family (>=1000 injected-instruction) for the
    corpus-level leakage checks below; generation is offline and fast (a few seconds)."""
    rng = random.Random(20260922)
    scenarios = list(iter_scenarios(rng, families=tuple(ToolFamily), n_per_family=1500))
    renderer = OfflineTemplateRenderer()
    return [
        (latent, renderer.render(latent, random.Random(i))) for i, latent in enumerate(scenarios)
    ]


def test_no_instructed_target_argument_anywhere(rendered_corpus) -> None:
    for _latent, context in rendered_corpus:
        assert "instructed_target" not in context.proposed_action.arguments


def test_denylist_tokens_never_appear_in_rendered_context(rendered_corpus) -> None:
    for _latent, context in rendered_corpus:
        lowered = context.model_dump_json().lower()
        for token in _DENYLIST_TOKENS:
            assert token not in lowered


def test_argument_key_presence_rate_parity_between_injected_and_other(rendered_corpus) -> None:
    """Parity is computed overall (across all tool kinds pooled), not per tool kind: every
    argument key's presence rate must be within 0.05 whether or not the call's
    action_origin is injected_instruction."""
    assert len(rendered_corpus) >= 1000
    injected_counts: dict[str, int] = {}
    other_counts: dict[str, int] = {}
    n_injected = 0
    n_other = 0
    for latent, context in rendered_corpus:
        is_injected = latent.action_origin is ActionOrigin.INJECTED_INSTRUCTION
        counts = injected_counts if is_injected else other_counts
        n_injected += is_injected
        n_other += not is_injected
        for key in context.proposed_action.arguments:
            counts[key] = counts.get(key, 0) + 1
    assert n_injected >= 500
    for key in set(injected_counts) | set(other_counts):
        rate_injected = injected_counts.get(key, 0) / n_injected
        rate_other = other_counts.get(key, 0) / n_other
        assert abs(rate_injected - rate_other) < 0.05, (key, rate_injected, rate_other)


def test_injected_call_target_appears_in_its_own_observation_across_tool_kinds(
    rendered_corpus,
) -> None:
    """Every followed instruction is checkable from text: the call's target argument
    (or its resource_id, for tools with no target key) is always the identifier named
    in the instruction, so the label always has textual support."""
    checked = 0
    for latent, context in rendered_corpus:
        if latent.action_origin is not ActionOrigin.INJECTED_INSTRUCTION:
            continue
        target_info = _target_argument_key(latent)
        key = target_info[0] if target_info is not None else "resource_id"
        checked += 1
        observation_text = context.observations[0].content
        assert str(context.proposed_action.arguments[key]) in observation_text
    assert checked > 100


def test_not_followed_instruction_target_absent_from_call_args(rendered_corpus) -> None:
    """Untrusted-content-with-instruction examples where the call does NOT follow it
    (hard negatives and other non-injected origins) must not leak a target key's value
    into the observation text, since that value was drawn independently of the
    instruction."""
    checked = 0
    for latent, context in rendered_corpus:
        if latent.action_origin is ActionOrigin.INJECTED_INSTRUCTION:
            continue
        if not latent.untrusted_content_contains_instruction:
            continue
        target_info = _target_argument_key(latent)
        if target_info is None:
            continue
        key, _pool_kind = target_info
        checked += 1
        observation_text = context.observations[0].content
        assert str(context.proposed_action.arguments[key]) not in observation_text
    assert checked > 100


def test_observation_content_length_is_realistic(rendered_corpus) -> None:
    lengths = [len(obs.content) for _latent, ctx in rendered_corpus for obs in ctx.observations]
    assert len(lengths) > 500
    assert all(150 <= length <= 2500 for length in lengths)
    median = sorted(lengths)[len(lengths) // 2]
    assert 300 <= median <= 2000
