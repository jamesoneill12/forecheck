from __future__ import annotations

from typing import Any

from tests.api.conftest import build_classify_body

TOKEN = "s3cr3t-test-token"


async def test_static_token_missing_is_401(client_factory: Any) -> None:
    client = await client_factory(auth_mode="static_token", static_token=TOKEN)
    response = await client.post("/v1/classify", json=build_classify_body())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_static_token_wrong_is_401(client_factory: Any) -> None:
    client = await client_factory(auth_mode="static_token", static_token=TOKEN)
    response = await client.post(
        "/v1/classify",
        json=build_classify_body(),
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


async def test_static_token_correct_is_200(client_factory: Any) -> None:
    client = await client_factory(auth_mode="static_token", static_token=TOKEN)
    response = await client.post(
        "/v1/classify",
        json=build_classify_body(),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200


async def test_header_passthrough_missing_header_is_401(client_factory: Any) -> None:
    client = await client_factory(auth_mode="header_passthrough")
    response = await client.post("/v1/classify", json=build_classify_body())
    assert response.status_code == 401


async def test_header_passthrough_present_header_is_200(client_factory: Any) -> None:
    client = await client_factory(auth_mode="header_passthrough")
    response = await client.post(
        "/v1/classify",
        json=build_classify_body(),
        headers={"X-Forecheck-Principal": "gateway-user-1"},
    )
    assert response.status_code == 200
