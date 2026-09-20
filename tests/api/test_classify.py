from __future__ import annotations

import time
from typing import TYPE_CHECKING

from forecheck.contracts import LABEL_SCHEMA_VERSION, ModelInfo, RiskDimension, TruncationInfo
from forecheck.inference.base import BackendCapabilities, BaseBackend, RawScores
from forecheck.inference.prompt import prompt_contract_hash
from tests.api.conftest import build_classify_body

if TYPE_CHECKING:
    from collections.abc import Sequence

    from httpx import AsyncClient
    from pytest import MonkeyPatch

    from forecheck.contracts import ActionContext


async def test_classify_happy_path(
    client: AsyncClient, valid_classify_body: dict[str, object]
) -> None:
    response = await client.post("/v1/classify", json=valid_classify_body)
    assert response.status_code == 200
    body = response.json()
    assert body["calibration"]["method"] == "none"
    assert len(body["scores"]) == len(list(RiskDimension))
    for score in body["scores"]:
        assert score["probability"] is None


async def test_classify_no_calibration_all_probabilities_null(
    client: AsyncClient, valid_classify_body: dict[str, object]
) -> None:
    response = await client.post("/v1/classify", json=valid_classify_body)
    body = response.json()
    assert body["calibration"]["method"] == "none"
    assert all(score["probability"] is None for score in body["scores"])


async def test_classify_batch_happy_path(
    client: AsyncClient, valid_classify_body: dict[str, object]
) -> None:
    payload = {"items": [valid_classify_body, valid_classify_body]}
    response = await client.post("/v1/classify/batch", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["abstained"] is False


class _FakeBackend(BaseBackend):
    def __init__(self, *, fail_tool_name: str | None = None, sleep_seconds: float = 0.0) -> None:
        self._fail_tool_name = fail_tool_name
        self._sleep_seconds = sleep_seconds

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            backend="fake",
            model_id="fake-1",
            prompt_contract_hash=prompt_contract_hash(),
            label_schema_version=LABEL_SCHEMA_VERSION,
        )

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_batching=True)

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        if self._sleep_seconds:
            time.sleep(self._sleep_seconds)
        if (
            self._fail_tool_name is not None
            and context.proposed_action.tool_name == self._fail_tool_name
        ):
            raise RuntimeError("synthetic backend failure")
        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        return RawScores(scores=dict.fromkeys(dims, 0.1), truncation=TruncationInfo())


async def test_batch_one_bad_item_does_not_fail_batch(
    monkeypatch: MonkeyPatch, client_factory: object
) -> None:
    from forecheck.api import deps as deps_module

    monkeypatch.setattr(deps_module, "MockBackend", lambda: _FakeBackend(fail_tool_name="boom"))
    client = await client_factory()  # type: ignore[operator]

    good = build_classify_body()
    bad = build_classify_body()
    bad["context"]["proposed_action"]["tool_name"] = "boom"
    response = await client.post("/v1/classify/batch", json={"items": [good, bad]})

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["abstained"] is False
    assert items[1]["abstained"] is True
    assert items[1]["scores"] == []


async def test_classify_timeout_returns_504(
    monkeypatch: MonkeyPatch, client_factory: object
) -> None:
    from forecheck.api import deps as deps_module

    monkeypatch.setattr(deps_module, "MockBackend", lambda: _FakeBackend(sleep_seconds=0.3))
    client = await client_factory()  # type: ignore[operator]

    body = build_classify_body()
    body["options"] = {"timeout_ms": 10}
    response = await client.post("/v1/classify", json=body)

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "backend_timeout"
