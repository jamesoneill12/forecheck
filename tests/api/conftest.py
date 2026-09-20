"""Shared fixtures for the API test suite. Every test uses the mock backend: no
network, no GPU, no torch."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from forecheck.api.app import create_app
from forecheck.api.settings import Settings
from forecheck.contracts import (
    ActionContext,
    AgentIdentity,
    Principal,
    ProposedAction,
    UserObjective,
)


def make_settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {"backend": "mock"}
    defaults.update(overrides)
    return Settings(**defaults)


def make_action_context(**overrides: Any) -> ActionContext:
    defaults: dict[str, Any] = {
        "objective": UserObjective(text="Read the quarterly report.", authorization_explicit=True),
        "principal": Principal(id="user-1"),
        "agent": AgentIdentity(id="agent-1", delegated_scopes=["*"]),
        "proposed_action": ProposedAction(tool_name="read_document"),
    }
    defaults.update(overrides)
    return ActionContext(**defaults)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(make_settings())
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as ac,
    ):
        yield ac


@pytest_asyncio.fixture
async def client_factory() -> AsyncIterator[Any]:
    created: list[Any] = []

    async def _make(**settings_overrides: Any) -> AsyncClient:
        app = create_app(make_settings(**settings_overrides))
        transport = ASGITransport(app=app)
        lifespan_cm = app.router.lifespan_context(app)
        await lifespan_cm.__aenter__()
        client = AsyncClient(transport=transport, base_url="http://testserver")
        created.append((lifespan_cm, client))
        return client

    yield _make

    for lifespan_cm, client in created:
        await client.aclose()
        await lifespan_cm.__aexit__(None, None, None)


def build_classify_body() -> dict[str, Any]:
    return {
        "context": {
            "objective": {"text": "Read the quarterly report.", "authorization_explicit": True},
            "principal": {"id": "user-1"},
            "agent": {"id": "agent-1", "delegated_scopes": ["*"]},
            "proposed_action": {"tool_name": "read_document"},
        }
    }


@pytest.fixture
def valid_classify_body() -> dict[str, Any]:
    return build_classify_body()
