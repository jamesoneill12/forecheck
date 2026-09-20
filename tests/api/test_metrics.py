from __future__ import annotations

from typing import TYPE_CHECKING

from tests.api.conftest import build_classify_body

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_metrics_contains_expected_names(client: AsyncClient) -> None:
    await client.post("/v1/classify", json=build_classify_body())
    response = await client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    for name in (
        "forecheck_requests_total",
        "forecheck_request_latency_seconds",
        "forecheck_dimension_probability",
        "forecheck_decisions_total",
        "forecheck_model_ready",
        "forecheck_abstentions_total",
    ):
        assert name in body
    assert "forecheck_model_ready 1.0" in body
