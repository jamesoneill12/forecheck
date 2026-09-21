"""``POST /v1/feedback`` — capture a human outcome on a prior forecheck decision.

This is the label flywheel: an approval, rejection, modification, escalation or expiry
on a ``REVIEW`` (or any) decision is a label on a real action. It never changes a
decision retroactively; it only feeds recalibration and policy-threshold refitting.
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends

from forecheck.api import audit
from forecheck.api.auth import Principal
from forecheck.api.deps import AppState, get_app_state, require_principal
from forecheck.contracts.io import FeedbackAck, FeedbackRecord

__all__ = ["router"]

router = APIRouter(tags=["feedback"])


@router.post("/v1/feedback", response_model=FeedbackAck)
async def submit_feedback(
    payload: FeedbackRecord,
    principal: Annotated[Principal, Depends(require_principal)],
    state: Annotated[AppState, Depends(get_app_state)],
) -> FeedbackAck:
    """Validate and append one feedback record to the configured sink."""
    feedback_id = payload.feedback_id or str(uuid4())
    record = (
        payload if payload.feedback_id else payload.model_copy(update={"feedback_id": feedback_id})
    )
    state.feedback_sink.append(record)
    audit.emit(audit.build_feedback_event(record=record, tenant_id=principal.tenant_id))
    return FeedbackAck(feedback_id=feedback_id)
