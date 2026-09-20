from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tests.api.conftest import build_classify_body

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient
    from pytest import CaptureFixture

SECRET = "sk-live-SECRET-do-not-log"


async def test_audit_log_never_contains_secret(
    client: AsyncClient, capsys: CaptureFixture[str]
) -> None:
    body = build_classify_body()
    body["context"]["proposed_action"]["arguments"] = {"api_key": SECRET}
    body["context"]["objective"]["text"] = f"Please use {SECRET} to authenticate."
    response = await client.post("/v1/classify", json=body)
    assert response.status_code == 200

    captured = capsys.readouterr().out
    assert SECRET not in captured
    assert "forecheck_audit" in captured
    assert "arguments_sha256" in captured


async def test_stored_body_never_contains_secret(client_factory: Any, tmp_path: Path) -> None:
    client = await client_factory(store_request_bodies=True, store_request_bodies_path=tmp_path)
    body = build_classify_body()
    body["context"]["proposed_action"]["arguments"] = {"token": SECRET}
    response = await client.post("/v1/classify", json=body)
    assert response.status_code == 200

    stored_files = list(tmp_path.glob("*.json"))
    assert stored_files
    for stored in stored_files:
        content = stored.read_text(encoding="utf-8")
        assert SECRET not in content
        json.loads(content)
