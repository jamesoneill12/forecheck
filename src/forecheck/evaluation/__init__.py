"""The forecheck evaluation suite.

Turns a :class:`~forecheck.inference.base.ClassifierBackend` plus a set of
:class:`~forecheck.contracts.Example` rows into an auditable
:class:`~forecheck.evaluation.report.EvaluationReport`: per-dimension classification
and calibration metrics, slice breakdowns, contrastive-pair consistency, selective-risk
curves, policy-decision cost metrics and a latency harness.

This package depends only on :mod:`forecheck.contracts` and the protocol/base classes
in :mod:`forecheck.inference.base`, :mod:`forecheck.calibration.base` and
:mod:`forecheck.policies.base` — never on a concrete backend, calibrator or policy
engine implementation.
"""

from __future__ import annotations

from forecheck.evaluation.report import EvaluationClass, EvaluationReport
from forecheck.evaluation.runner import evaluate

__all__ = ["EvaluationClass", "EvaluationReport", "evaluate"]
