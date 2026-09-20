from __future__ import annotations

from typing import TYPE_CHECKING

from forecheck.contracts import (
    LABEL_SCHEMA_VERSION,
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    DimensionScore,
    ModelInfo,
    RiskDimension,
)
from forecheck.inference.prompt import prompt_contract_hash
from tests.api.conftest import build_classify_body

if TYPE_CHECKING:
    from httpx import AsyncClient


def _calibrated_classification(prompt_injection: float) -> dict[str, object]:
    response = ClassifyResponse(
        scores=[
            DimensionScore(
                dimension=RiskDimension.PROMPT_INJECTION_INFLUENCE,
                probability=prompt_injection,
                calibrated=True,
            ),
        ],
        model=ModelInfo(
            backend="mock",
            model_id="mock-heuristic-v1",
            prompt_contract_hash=prompt_contract_hash(),
            label_schema_version=LABEL_SCHEMA_VERSION,
        ),
        calibration=CalibrationInfo(method=CalibrationMethod.TEMPERATURE),
        latency_ms=1.0,
    )
    return response.model_dump(mode="json")


async def test_list_policies(client: AsyncClient) -> None:
    response = await client.get("/v1/policies")
    assert response.status_code == 200
    bundles = response.json()
    assert {b["bundle_id"] for b in bundles} == {"conservative", "balanced", "permissive"}
    for bundle in bundles:
        assert bundle["bundle_hash"]


async def test_evaluate_with_context_classifies_then_evaluates(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policies/evaluate", json={"context": build_classify_body()["context"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] is not None
    assert "matched_rules" in body
    assert body["policy_bundle_id"] == "conservative"


async def test_evaluate_with_calibrated_classification_matches_rules(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policies/evaluate", json={"classification": _calibrated_classification(0.9)}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "deny"
    rule_ids = {m["rule_id"] for m in body["matched_rules"]}
    assert "injection_drives_mutation" in rule_ids


async def test_evaluate_with_both_inputs_is_422(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policies/evaluate",
        json={
            "classification": _calibrated_classification(0.9),
            "context": build_classify_body()["context"],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


async def test_policy_bundle_header_outside_allowlist_is_403(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policies/evaluate",
        json={"context": build_classify_body()["context"]},
        headers={"X-Forecheck-Policy-Bundle": "nonexistent"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_policy_bundle_header_in_allowlist_selects_bundle(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policies/evaluate",
        json={"context": build_classify_body()["context"]},
        headers={"X-Forecheck-Policy-Bundle": "permissive"},
    )
    assert response.status_code == 200
    assert response.json()["policy_bundle_id"] == "permissive"
