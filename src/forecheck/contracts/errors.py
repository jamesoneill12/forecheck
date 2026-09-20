"""Stable error envelope.

The HTTP status is advisory; ``error.code`` is the contract. Details never echo
request content, because request bodies can contain secrets and the error path is the
most commonly logged path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from forecheck.contracts.enums import ErrorCode
from forecheck.contracts.io import SCHEMA_VERSION, SchemaVersion

__all__ = ["HTTP_STATUS_FOR_CODE", "ErrorBody", "ErrorResponse", "ForecheckError"]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ErrorCode
    message: str
    field_path: str | None = Field(
        default=None, description="Dotted path to the offending field, never its value."
    )
    retryable: bool = False


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: SchemaVersion = SCHEMA_VERSION
    request_id: str | None = None
    error: ErrorBody


HTTP_STATUS_FOR_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.UNSUPPORTED_SCHEMA_VERSION: 400,
    ErrorCode.REQUEST_TOO_LARGE: 413,
    ErrorCode.TOO_MANY_TRAJECTORY_STEPS: 422,
    ErrorCode.CONTEXT_TOO_LONG: 422,
    ErrorCode.MODEL_NOT_READY: 503,
    ErrorCode.BACKEND_TIMEOUT: 504,
    ErrorCode.BACKEND_ERROR: 502,
    ErrorCode.POLICY_BUNDLE_NOT_FOUND: 404,
    ErrorCode.POLICY_BUNDLE_INVALID: 422,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
}

_RETRYABLE = {
    ErrorCode.MODEL_NOT_READY,
    ErrorCode.BACKEND_TIMEOUT,
    ErrorCode.BACKEND_ERROR,
    ErrorCode.RATE_LIMITED,
}


class ForecheckError(Exception):
    """Raised inside the service and rendered into :class:`ErrorResponse`."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        field_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_path = field_path

    @property
    def http_status(self) -> int:
        return HTTP_STATUS_FOR_CODE[self.code]

    def to_body(self) -> ErrorBody:
        return ErrorBody(
            code=self.code,
            message=self.message,
            field_path=self.field_path,
            retryable=self.code in _RETRYABLE,
        )
