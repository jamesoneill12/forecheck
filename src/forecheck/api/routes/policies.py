"""``POST /v1/policies/evaluate`` and ``GET /v1/policies``."""

from __future__ import annotations

from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from forecheck.api import audit, metrics
from forecheck.api.auth import Principal
from forecheck.api.deps import (
    AppState,
    get_app_state,
    get_policy_engine,
    get_settings,
    require_principal,
    resolve_policy_bundle_id,
)
from forecheck.api.settings import Settings
from forecheck.contracts import (
    ClassifyRequest,
    ClassifyResponse,
    Decision,
    PolicyDecision,
    PolicyEvaluateRequest,
)

__all__ = ["router"]

router = APIRouter(tags=["policies"])


class PolicyBundleInfo(BaseModel):
    bundle_id: str
    bundle_hash: str
    version: int
    description: str
    default_decision: Decision


@router.post("/v1/policies/evaluate", response_model=PolicyDecision)
async def evaluate_policy(
    payload: PolicyEvaluateRequest,
    principal: Annotated[Principal, Depends(require_principal)],
    state: Annotated[AppState, Depends(get_app_state)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_forecheck_policy_bundle: Annotated[str | None, Header()] = None,
) -> PolicyDecision:
    """Evaluate a policy bundle against either a supplied classification or a context
    the service classifies first. Exactly one of ``classification``/``context`` is
    required (enforced by the contract itself)."""
    bundle_id = resolve_policy_bundle_id(
        header_value=x_forecheck_policy_bundle,
        body_value=payload.policy_bundle_id,
        settings=settings,
    )
    policy_engine = get_policy_engine(state, bundle_id)

    classification: ClassifyResponse
    if payload.classification is not None:
        classification = payload.classification
        context = payload.context
    else:
        context = payload.context
        assert context is not None
        classify_request = ClassifyRequest(request_id=payload.request_id, context=context)
        classification = await anyio.to_thread.run_sync(state.classifier.classify, classify_request)

    decision = policy_engine.evaluate(classification, context)
    metrics.DECISIONS_TOTAL.labels(
        decision=decision.decision.value, bundle=decision.policy_bundle_id
    ).inc()
    audit.emit(
        audit.build_policy_event(
            request_id=decision.request_id, tenant_id=principal.tenant_id, decision=decision
        )
    )
    return decision


@router.get("/v1/policies", response_model=list[PolicyBundleInfo])
async def list_policies(
    state: Annotated[AppState, Depends(get_app_state)],
) -> list[PolicyBundleInfo]:
    """List every policy bundle loaded at startup, with its id and content hash."""
    return [
        PolicyBundleInfo(
            bundle_id=engine.bundle_id,
            bundle_hash=engine.bundle_hash,
            version=engine.bundle.version,
            description=engine.bundle.description,
            default_decision=engine.default_decision,
        )
        for engine in state.policy_engines.values()
    ]
