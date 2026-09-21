"""Renders an :class:`ActionContext` into the canonical text defined by the prompt
contract in :mod:`forecheck.inference.prompt`.

Two properties are load-bearing:

* **Determinism.** The same context always renders to the same string, field order is
  fixed by :data:`~forecheck.inference.prompt.SECTION_ORDER`, and mapping-valued fields
  are rendered in sorted-key order rather than insertion order.
* **Non-forgeability.** Every interpolated field value is escaped (``<`` and ``>``
  become ``&lt;``/``&gt;``) before being placed inside a fenced section, so content
  supplied by an untrusted observation cannot emit a literal ``<tag ...>`` sequence and
  make itself look like a different, more trusted section.

When the rendering exceeds a token budget, content is dropped in a fixed priority
order -- oldest untrusted observations first, then oldest trajectory steps -- and the
drop is reported back via :class:`~forecheck.contracts.TruncationInfo`. The proposed
action, principal, agent, destination, and policies are never dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

from forecheck.contracts import (
    ActionContext,
    Limits,
    Observation,
    TrajectoryStep,
    TruncationInfo,
    TrustLevel,
)
from forecheck.inference.prompt import SECTION_ORDER, SYSTEM_PREAMBLE

__all__ = ["SerializedContext", "estimate_tokens", "render_context", "serialize_context"]

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimate: ceil(len(text) / 4).

    This intentionally does not require a tokenizer. It is a rough proxy used only to
    decide when truncation is necessary, not to bound cost precisely.
    """
    if not text:
        return 0
    return -(-len(text) // _CHARS_PER_TOKEN)


def _escape(value: str) -> str:
    return value.replace("<", "&lt;").replace(">", "&gt;")


def _tag(name: str, /, **attrs: str) -> str:
    if not attrs:
        return f"<{name}>"
    attr_str = " ".join(f"{key}={_escape(str(val))}" for key, val in attrs.items())
    return f"<{name} {attr_str}>"


def _close_tag(name: str) -> str:
    return f"</{name}>"


def _format_mapping(mapping: dict[str, object]) -> str:
    if not mapping:
        return "(none)"
    lines = [f"  {_escape(str(k))}: {_escape(str(mapping[k]))}" for k in sorted(mapping)]
    return "\n".join(lines)


def _format_list(items: list[str]) -> str:
    if not items:
        return "(none)"
    return ", ".join(_escape(str(item)) for item in sorted(items))


def _render_system() -> str:
    return f"{_tag('system')}\n{_escape(SYSTEM_PREAMBLE)}\n{_close_tag('system')}"


def _render_objective(context: ActionContext) -> str:
    obj = context.objective
    body = (
        f"text: {_escape(obj.text)}\n"
        f"authorization_explicit: {obj.authorization_explicit}\n"
        f"stated_at: {obj.stated_at.isoformat() if obj.stated_at else 'unknown'}"
    )
    return f"{_tag('objective', trust=obj.trust.value)}\n{body}\n{_close_tag('objective')}"


def _render_principal(context: ActionContext, *, strip_identity: bool = False) -> str:
    p = context.principal
    lines = [
        f"id: {_escape(p.id)}",
        f"type: {p.type.value}",
        f"tenant_id: {_escape(p.tenant_id) if p.tenant_id else 'unknown'}",
        f"roles: {_format_list(p.roles)}",
    ]
    if not strip_identity:
        lines.append(f"entitlements: {_format_list(p.entitlements)}")
    lines.append(f"auth_method: {p.auth_method.value}")
    lines.append(f"mfa_satisfied: {p.mfa_satisfied}")
    body = "\n".join(lines)
    return (
        f"{_tag('principal', trust=TrustLevel.PRINCIPAL.value)}\n{body}\n{_close_tag('principal')}"
    )


def _render_agent(context: ActionContext, *, strip_identity: bool = False) -> str:
    a = context.agent
    lines = [
        f"id: {_escape(a.id)}",
        f"name: {_escape(a.name) if a.name else 'unknown'}",
        f"version: {_escape(a.version) if a.version else 'unknown'}",
    ]
    if not strip_identity:
        lines.append(f"delegated_scopes: {_format_list(a.delegated_scopes)}")
        lines.append(f"on_behalf_of: {_escape(a.on_behalf_of) if a.on_behalf_of else 'none'}")
    body = "\n".join(lines)
    return f"{_tag('agent', trust=TrustLevel.SYSTEM.value)}\n{body}\n{_close_tag('agent')}"


def _render_environment(context: ActionContext) -> str:
    e = context.environment
    body = (
        f"stage: {e.stage.value}\n"
        f"region: {_escape(e.region) if e.region else 'unknown'}\n"
        f"change_freeze: {e.change_freeze}\n"
        f"labels:\n{_format_mapping(dict(e.labels))}"
    )
    return (
        f"{_tag('environment', trust=TrustLevel.SYSTEM.value)}\n{body}\n{_close_tag('environment')}"
    )


def _render_resources(context: ActionContext) -> str:
    if not context.resources:
        return (
            f"{_tag('resources', trust=TrustLevel.SYSTEM.value)}\n(none)\n{_close_tag('resources')}"
        )
    lines = []
    for r in context.resources:
        lines.append(
            f"- urn={_escape(r.urn)} kind={r.kind.value} sensitivity={r.sensitivity.value} "
            f"operation={r.operation.value} reversible={r.reversible} "
            f"record_count_estimate={r.record_count_estimate} "
            f"owner={_escape(r.owner) if r.owner else 'unknown'}"
        )
    body = "\n".join(lines)
    return f"{_tag('resources', trust=TrustLevel.SYSTEM.value)}\n{body}\n{_close_tag('resources')}"


def _render_destination(context: ActionContext) -> str:
    d = context.destination
    if d is None:
        tag = _tag("destination", trust=TrustLevel.SYSTEM.value)
        return f"{tag}\n(none)\n{_close_tag('destination')}"
    body = (
        f"identifier: {_escape(d.identifier)}\n"
        f"relationship: {d.relationship.value}\n"
        f"resembles: {_escape(d.resembles) if d.resembles else 'none'}\n"
        f"verified: {d.verified}"
    )
    return f"{_tag('destination', trust=d.trust.value)}\n{body}\n{_close_tag('destination')}"


def _render_financial(context: ActionContext) -> str:
    f = context.financial
    if f is None:
        return (
            f"{_tag('financial', trust=TrustLevel.SYSTEM.value)}\n(none)\n{_close_tag('financial')}"
        )
    body = (
        f"amount: {f.amount}\n"
        f"currency: {f.currency}\n"
        f"recurring: {f.recurring}\n"
        f"counterparty: {_escape(f.counterparty) if f.counterparty else 'unknown'}"
    )
    return f"{_tag('financial', trust=TrustLevel.SYSTEM.value)}\n{body}\n{_close_tag('financial')}"


def _render_policies(context: ActionContext, *, strip_identity: bool = False) -> str:
    if not context.policies:
        return (
            f"{_tag('policies', trust=TrustLevel.SYSTEM.value)}\n(none)\n{_close_tag('policies')}"
        )
    lines = [
        f"- id={_escape(p.id)} scope={_escape(p.scope) if p.scope else 'unknown'} "
        f"severity={_escape(p.severity) if p.severity else 'unknown'}"
        + ("" if strip_identity else f": {_escape(p.text)}")
        for p in context.policies
    ]
    body = "\n".join(lines)
    return f"{_tag('policies', trust=TrustLevel.SYSTEM.value)}\n{body}\n{_close_tag('policies')}"


def _render_trajectory_step(step: TrajectoryStep) -> str:
    args = _format_mapping(dict(step.arguments)) if step.arguments is not None else "(digest only)"
    body = (
        f"index: {step.index}\n"
        f"tool_name: {_escape(step.tool_name)}\n"
        f"arguments_digest: {_escape(step.arguments_digest) if step.arguments_digest else 'none'}\n"
        f"arguments:\n{args}\n"
        f"outcome: {_escape(step.outcome) if step.outcome else 'unknown'}\n"
        f"result_summary: {_escape(step.result_summary) if step.result_summary else 'none'}"
    )
    tag = _tag("trajectory_step", trust=step.result_trust.value, index=str(step.index))
    return f"{tag}\n{body}\n{_close_tag('trajectory_step')}"


def _render_trajectory(steps: list[TrajectoryStep]) -> str:
    if not steps:
        return f"{_tag('trajectory')}\n(none)\n{_close_tag('trajectory')}"
    body = "\n".join(_render_trajectory_step(s) for s in steps)
    return f"{_tag('trajectory')}\n{body}\n{_close_tag('trajectory')}"


def _render_observation(obs: Observation) -> str:
    body = (
        f"id: {_escape(obs.id)}\n"
        f"source: {_escape(obs.source)}\n"
        f"content_type: {_escape(obs.content_type) if obs.content_type else 'unknown'}\n"
        f"content: {_escape(obs.content)}"
    )
    tag = _tag("observation", trust=obs.trust.value, source=obs.source, id=obs.id)
    return f"{tag}\n{body}\n{_close_tag('observation')}"


def _render_observations(observations: list[Observation]) -> str:
    if not observations:
        return f"{_tag('observations')}\n(none)\n{_close_tag('observations')}"
    body = "\n".join(_render_observation(o) for o in observations)
    return f"{_tag('observations')}\n{body}\n{_close_tag('observations')}"


def _render_proposed_action(context: ActionContext) -> str:
    pa = context.proposed_action
    body = (
        f"tool_name: {_escape(pa.tool_name)}\n"
        f"tool_description: {_escape(pa.tool_description) if pa.tool_description else 'none'}\n"
        f"tool_family: {pa.tool_family.value if pa.tool_family else 'unknown'}\n"
        f"server: {_escape(pa.server) if pa.server else 'unknown'}\n"
        f"idempotent: {pa.idempotent}\n"
        f"arguments:\n{_format_mapping(dict(pa.arguments))}"
    )
    tag = _tag("proposed_action", trust=TrustLevel.SYSTEM.value)
    return f"{tag}\n{body}\n{_close_tag('proposed_action')}"


_SECTION_RENDERERS = {
    "system": lambda ctx, obs, traj, strip: _render_system(),
    "objective": lambda ctx, obs, traj, strip: _render_objective(ctx),
    "principal": lambda ctx, obs, traj, strip: _render_principal(ctx, strip_identity=strip),
    "agent": lambda ctx, obs, traj, strip: _render_agent(ctx, strip_identity=strip),
    "environment": lambda ctx, obs, traj, strip: _render_environment(ctx),
    "resources": lambda ctx, obs, traj, strip: _render_resources(ctx),
    "destination": lambda ctx, obs, traj, strip: _render_destination(ctx),
    "financial": lambda ctx, obs, traj, strip: _render_financial(ctx),
    "policies": lambda ctx, obs, traj, strip: _render_policies(ctx, strip_identity=strip),
    "trajectory": lambda ctx, obs, traj, strip: _render_trajectory(traj),
    "observations": lambda ctx, obs, traj, strip: _render_observations(obs),
    "proposed_action": lambda ctx, obs, traj, strip: _render_proposed_action(ctx),
}


def _render(
    context: ActionContext,
    observations: list[Observation],
    trajectory: list[TrajectoryStep],
    *,
    strip_identity: bool = False,
) -> str:
    sections = [
        _SECTION_RENDERERS[name](context, observations, trajectory, strip_identity)
        for name in SECTION_ORDER
    ]
    return "\n\n".join(sections)


@dataclass(frozen=True, slots=True)
class SerializedContext:
    text: str
    truncation: TruncationInfo
    estimated_tokens: int


def serialize_context(
    context: ActionContext,
    *,
    max_tokens: int = Limits.MAX_PROMPT_TOKENS,
    strip_identity: bool = False,
) -> SerializedContext:
    """Render ``context`` to canonical text, truncating if it exceeds ``max_tokens``.

    Truncation drops, in order: oldest untrusted observations, then oldest trajectory
    steps (by ascending index). The proposed action, principal, agent, destination,
    and policies are never dropped.

    ``strip_identity`` is the identity-ablation switch: when set, it omits the
    principal's entitlements, the agent's delegated scopes and delegation chain
    (``on_behalf_of``), and each policy statement's free text, leaving every other
    field -- and the section structure itself -- unchanged. Used to test whether a
    backend's score depends on authorization context rather than the action itself.
    """
    observations = list(context.observations)
    trajectory = list(context.trajectory)
    original_text = _render(context, observations, trajectory, strip_identity=strip_identity)
    text = original_text
    tokens = estimate_tokens(text)
    dropped_observations = 0
    dropped_trajectory = 0

    while tokens > max_tokens:
        untrusted_idx = next(
            (i for i, o in enumerate(observations) if o.trust is TrustLevel.UNTRUSTED), None
        )
        if untrusted_idx is not None:
            observations.pop(untrusted_idx)
            dropped_observations += 1
        elif trajectory:
            trajectory.pop(0)
            dropped_trajectory += 1
        else:
            break
        text = _render(context, observations, trajectory, strip_identity=strip_identity)
        tokens = estimate_tokens(text)

    truncated = dropped_observations > 0 or dropped_trajectory > 0
    truncation = TruncationInfo(
        truncated=truncated,
        dropped_trajectory_steps=dropped_trajectory,
        dropped_observations=dropped_observations,
        dropped_characters=max(0, len(original_text) - len(text)),
    )
    return SerializedContext(text=text, truncation=truncation, estimated_tokens=tokens)


def render_context(context: ActionContext, *, strip_identity: bool = False) -> str:
    """Convenience wrapper returning only the rendered text, at the default budget."""
    return serialize_context(context, strip_identity=strip_identity).text
