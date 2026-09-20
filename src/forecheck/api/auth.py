"""Pluggable authentication.

``AuthProvider`` is the extension point: ship three implementations and let callers
supply their own by satisfying the same ``Protocol``. Every implementation either
returns a :class:`Principal` or raises :class:`~forecheck.contracts.ForecheckError`
with ``UNAUTHENTICATED`` or ``FORBIDDEN``.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from forecheck.contracts import ErrorCode, ForecheckError

if TYPE_CHECKING:
    from starlette.requests import Request

__all__ = [
    "AuthProvider",
    "HeaderPassthroughAuth",
    "NoAuth",
    "Principal",
    "StaticTokenAuth",
]


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str | None = None


@runtime_checkable
class AuthProvider(Protocol):
    def authenticate(self, request: Request) -> Principal: ...


class NoAuth:
    """Accepts every request as an anonymous principal. The default."""

    def authenticate(self, request: Request) -> Principal:
        del request
        return Principal(principal_id="anonymous", tenant_id=None)


class StaticTokenAuth:
    """Constant-time bearer-token check against a single configured secret."""

    def __init__(self, token: str, *, tenant_header_name: str = "X-Forecheck-Tenant-Id") -> None:
        self._token = token
        self._tenant_header_name = tenant_header_name

    def authenticate(self, request: Request) -> Principal:
        header = request.headers.get("authorization")
        if header is None or not header.lower().startswith("bearer "):
            raise ForecheckError(ErrorCode.UNAUTHENTICATED, "missing bearer token")
        candidate = header[len("bearer ") :]
        if not hmac.compare_digest(candidate, self._token):
            raise ForecheckError(ErrorCode.UNAUTHENTICATED, "invalid bearer token")
        tenant_id = request.headers.get(self._tenant_header_name)
        return Principal(principal_id="static-token-client", tenant_id=tenant_id)


class HeaderPassthroughAuth:
    """Trusts an identity header set by an upstream gateway.

    This provider performs no cryptographic verification of its own; it is only safe
    when the gateway is the sole path into the service and strips the header from any
    request it did not itself set.
    """

    def __init__(
        self, header_name: str, *, tenant_header_name: str = "X-Forecheck-Tenant-Id"
    ) -> None:
        self._header_name = header_name
        self._tenant_header_name = tenant_header_name

    def authenticate(self, request: Request) -> Principal:
        value = request.headers.get(self._header_name)
        if not value:
            raise ForecheckError(
                ErrorCode.UNAUTHENTICATED, f"missing identity header {self._header_name!r}"
            )
        tenant_id = request.headers.get(self._tenant_header_name)
        return Principal(principal_id=value, tenant_id=tenant_id)
