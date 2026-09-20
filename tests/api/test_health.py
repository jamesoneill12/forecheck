from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from forecheck.api.app import create_app
from tests.api.conftest import make_settings


async def test_live_always_200_without_lifespan() -> None:
    app = create_app(make_settings())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


async def test_ready_is_503_before_lifespan() -> None:
    from forecheck.api.deps import build_app_state

    app = create_app(make_settings())
    transport = ASGITransport(app=app)
    app.state.forecheck = await build_app_state(make_settings())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_ready"


async def test_ready_is_200_after_lifespan(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


async def test_version_fields_present(client: AsyncClient) -> None:
    response = await client.get("/version")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "forecheck_version",
        "schema_version",
        "label_schema_version",
        "prompt_contract_hash",
        "backend",
        "model_id",
        "calibration_artifact_id",
        "policy_bundles",
        "device",
        "torch_available",
    ):
        assert field in body
    assert body["calibration_artifact_id"] is None
    assert body["backend"] == "mock"
    assert len(body["policy_bundles"]) >= 1
