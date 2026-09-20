"""Quickstart for :class:`~forecheck.integrations.sdk.ForecheckClient`.

Runs entirely offline: an ``httpx.MockTransport`` answers every request using a
``LocalForecheck`` instance (mock backend), so the example exercises the real HTTP
request/response shapes without a running service. Point ``ForecheckClient`` at a real
``base_url`` in production; nothing else about this script changes.
"""

from __future__ import annotations

import httpx

from forecheck.contracts import (
    ActionContext,
    BatchClassifyRequest,
    ClassifyRequest,
    PolicyEvaluateRequest,
    PrincipalType,
)
from forecheck.integrations.context_builder import ActionContextBuilder
from forecheck.integrations.local import LocalForecheck
from forecheck.integrations.sdk import ForecheckClient


def build_benign_context() -> ActionContext:
    return (
        ActionContextBuilder()
        .objective("Look up the status of ticket #4821", explicit=True)
        .principal("user-1", type=PrincipalType.HUMAN, roles=["support_agent"])
        .agent("agent-1", delegated_scopes=["tickets:read"])
        .propose("get_ticket", arguments={"ticket_id": 4821})
        .build()
    )


def make_mock_transport(forecheck: LocalForecheck) -> httpx.MockTransport:
    """A tiny fake server: forwards each route to an in-process LocalForecheck."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/classify":
            body = ClassifyRequest.model_validate_json(request.content)
            response = forecheck.classify(body)
            return httpx.Response(200, json=response.model_dump(mode="json"))
        if request.url.path == "/v1/classify/batch":
            batch = BatchClassifyRequest.model_validate_json(request.content)
            items = [forecheck.classify(item) for item in batch.items]
            payload = {"items": [item.model_dump(mode="json") for item in items]}
            return httpx.Response(200, json=payload)
        if request.url.path == "/v1/policies/evaluate":
            body = PolicyEvaluateRequest.model_validate_json(request.content)
            decision = forecheck.evaluate(body)
            return httpx.Response(200, json=decision.model_dump(mode="json"))
        if request.url.path == "/health/ready":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/health/live":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/version":
            return httpx.Response(200, json={"schema_version": "1.0"})
        return httpx.Response(
            404,
            json={
                "schema_version": "1.0",
                "error": {"code": "internal_error", "message": "no route", "retryable": False},
            },
        )

    return httpx.MockTransport(handler)


def main() -> None:
    forecheck = LocalForecheck()
    transport = make_mock_transport(forecheck)

    with ForecheckClient("https://forecheck.example", transport=transport) as client:
        print("ready:", client.ready())
        print("version:", client.version())

        context = build_benign_context()
        classify_request = ClassifyRequest(context=context)
        classification = client.classify(classify_request)
        print("classification abstained:", classification.abstained)

        decision = client.classify_and_evaluate(context)
        print("decision:", decision.decision.value)
        print("matched_rules:", [rule.rule_id for rule in decision.matched_rules])
        print("bundle_hash:", decision.policy_bundle_hash[:16] + "...")


if __name__ == "__main__":
    main()
