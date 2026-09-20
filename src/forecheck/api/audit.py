"""Structured audit events with redaction baked in.

Every event here is built from typed facts, never from free text: no objective text,
no observation content, no argument values, no policy text. Argument values are
represented only as ``arguments_sha256``. See ``docs/threat-model.md`` FC-06.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from forecheck.api.redaction import digest_json

if TYPE_CHECKING:
    from forecheck.contracts import ActionContext, ClassifyResponse, PolicyDecision

__all__ = ["build_classify_event", "build_policy_event", "emit", "logger", "store_event"]

logger = structlog.get_logger("forecheck.audit")


def _dimension_probabilities(
    response: ClassifyResponse, *, include_raw: bool
) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for score in response.scores:
        if score.probability is not None:
            values[score.dimension.value] = score.probability
        elif include_raw:
            values[score.dimension.value] = score.raw_score
        else:
            values[score.dimension.value] = None
    return values


def build_classify_event(
    *,
    request_id: str | None,
    tenant_id: str | None,
    context: ActionContext,
    response: ClassifyResponse,
    include_raw: bool,
) -> dict[str, Any]:
    return {
        "event_kind": "classify",
        "request_id": request_id,
        "tenant_id": tenant_id,
        "principal_id": context.principal.id,
        "agent_id": context.agent.id,
        "tool_name": context.proposed_action.tool_name,
        "arguments_sha256": digest_json(context.proposed_action.arguments),
        "n_observations": len(context.observations),
        "n_trajectory": len(context.trajectory),
        "dimension_probability": _dimension_probabilities(response, include_raw=include_raw),
        "abstained": response.abstained,
        "abstention_reasons": [r.value for r in response.abstention_reasons],
        "model_id": response.model.model_id,
        "prompt_contract_hash": response.model.prompt_contract_hash,
        "latency_ms": response.latency_ms,
    }


def build_policy_event(
    *,
    request_id: str | None,
    tenant_id: str | None,
    decision: PolicyDecision,
) -> dict[str, Any]:
    return {
        "event_kind": "policy_evaluate",
        "request_id": request_id,
        "tenant_id": tenant_id,
        "decision": decision.decision.value,
        "matched_rule_ids": [m.rule_id for m in decision.matched_rules],
        "policy_bundle_id": decision.policy_bundle_id,
        "policy_bundle_hash": decision.policy_bundle_hash,
    }


def emit(event: dict[str, Any]) -> None:
    logger.info("forecheck_audit", **event)


def store_event(sink_dir: Path, request_id: str | None, event: dict[str, Any]) -> None:
    """Persist an already-redacted audit event to a JSONL sink.

    Only called when ``FORECHECK_STORE_REQUEST_BODIES=true``; the event passed in is
    the same redacted structure that goes to the audit log, never the raw request
    body, so storage cannot reintroduce content the audit log excludes.
    """
    sink_dir.mkdir(parents=True, exist_ok=True)
    name = f"{request_id or 'unknown'}-{int(time.time() * 1000)}.json"
    (sink_dir / name).write_text(json.dumps(event, sort_keys=True), encoding="utf-8")
