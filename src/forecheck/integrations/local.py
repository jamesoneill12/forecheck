"""In-process forecheck: the same surface as :class:`~forecheck.integrations.sdk.ForecheckClient`
without an HTTP hop.

Constructs a :class:`~forecheck.inference.classifier.Classifier` and a
:class:`~forecheck.policies.engine.DeterministicPolicyEngine` directly. Useful for
tests, offline examples, and any deployment shape where the middleware runs in the same
process as the model (see ``docs/product-spec.md`` §12, deployment shape 1).

The default backend is :class:`~forecheck.inference.mock.MockBackend`, a deterministic
heuristic. **It is not a trained model and must not be used to make real access-control
decisions.** Pass a real ``ClassifierBackend`` for anything beyond examples and tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from forecheck.calibration.store import load_bundle
from forecheck.contracts import ClassifyRequest, ClassifyResponse, PolicyDecision
from forecheck.inference.classifier import Classifier
from forecheck.inference.mock import MockBackend
from forecheck.policies.builtin import builtin_bundle_path
from forecheck.policies.loader import load_policy_engine

if TYPE_CHECKING:
    from forecheck.contracts import ActionContext, PolicyEvaluateRequest
    from forecheck.inference.base import ClassifierBackend
    from forecheck.policies.engine import DeterministicPolicyEngine

__all__ = ["LocalForecheck"]


class LocalForecheck:
    """In-process ``classify`` / ``evaluate`` / ``classify_and_evaluate``, no network."""

    def __init__(
        self,
        backend: ClassifierBackend | None = None,
        calibration_path: Path | None = None,
        bundle: str = "conservative",
    ) -> None:
        self._backend: ClassifierBackend = backend or MockBackend()
        calibrator_bundle = load_bundle(calibration_path) if calibration_path is not None else None
        self._classifier = Classifier(self._backend, calibrator_bundle)
        self._default_bundle_name = bundle
        self._engines: dict[str, DeterministicPolicyEngine] = {
            bundle: load_policy_engine(builtin_bundle_path(bundle))
        }

    def _engine_for(self, bundle: str | None) -> DeterministicPolicyEngine:
        name = bundle or self._default_bundle_name
        if name not in self._engines:
            self._engines[name] = load_policy_engine(builtin_bundle_path(name))
        return self._engines[name]

    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        return self._classifier.classify(request)

    def evaluate(
        self, request: PolicyEvaluateRequest, *, bundle: str | None = None
    ) -> PolicyDecision:
        engine = self._engine_for(bundle)
        if request.classification is not None:
            return engine.evaluate(request.classification, request.context)
        context = request.context
        if context is None:  # pragma: no cover - contract already guarantees this
            raise ValueError("PolicyEvaluateRequest must supply 'classification' or 'context'")
        classification = self._classifier.classify(
            ClassifyRequest(request_id=request.request_id, context=context)
        )
        return engine.evaluate(classification, context)

    def classify_and_evaluate(
        self,
        context: ActionContext,
        *,
        bundle: str | None = None,
        request_id: str | None = None,
    ) -> PolicyDecision:
        classification = self._classifier.classify(
            ClassifyRequest(request_id=request_id, context=context)
        )
        return self._engine_for(bundle).evaluate(classification, context)
