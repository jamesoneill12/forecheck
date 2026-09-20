from __future__ import annotations

import json
from typing import TYPE_CHECKING

from forecheck.contracts import Limits
from tests.api.conftest import build_classify_body

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_oversized_body_is_413(client: AsyncClient) -> None:
    body = build_classify_body()
    body["context"]["objective"]["text"] = "a" * (Limits.MAX_REQUEST_BYTES + 1024)
    payload = json.dumps(body).encode("utf-8")
    response = await client.post(
        "/v1/classify", content=payload, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


async def test_unknown_field_is_422_with_field_path_and_no_value_echo(client: AsyncClient) -> None:
    body = build_classify_body()
    secret = "sk-live-SECRET-do-not-echo"
    body["not_a_real_field"] = secret
    response = await client.post("/v1/classify", json=body)
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_failed"
    assert payload["error"]["field_path"] is not None
    assert secret not in json.dumps(payload)


async def test_unsupported_schema_version_is_400(client: AsyncClient) -> None:
    body = build_classify_body()
    body["schema_version"] = "99.0"
    response = await client.post("/v1/classify", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_schema_version"


async def test_classify_no_calibration_method_is_none(client: AsyncClient) -> None:
    response = await client.post("/v1/classify", json=build_classify_body())
    body = response.json()
    assert body["calibration"]["method"] == "none"
    assert all(score["probability"] is None for score in body["scores"])
