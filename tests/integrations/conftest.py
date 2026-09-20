from __future__ import annotations

from forecheck.contracts import (
    ActionContext,
    AgentIdentity,
    Principal,
    ProposedAction,
    UserObjective,
)


def make_context(**overrides: object) -> ActionContext:
    defaults: dict[str, object] = {
        "objective": UserObjective(text="Read the quarterly report.", authorization_explicit=True),
        "principal": Principal(id="user-1"),
        "agent": AgentIdentity(id="agent-1", delegated_scopes=["docs:read"]),
        "proposed_action": ProposedAction(tool_name="read_document", arguments={"doc_id": 1}),
    }
    defaults.update(overrides)
    return ActionContext(**defaults)  # type: ignore[arg-type]
