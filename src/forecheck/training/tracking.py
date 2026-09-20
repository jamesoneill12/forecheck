"""Experiment tracking behind a narrow protocol so mlflow is never a hard dependency.

``LocalJsonTracker`` is the default: zero extra dependencies, writes plain JSON/JSONL
next to the run's other captured artifacts, and is what the CI smoke train uses.
``MlflowTracker`` lazily imports ``mlflow`` and gives a clear error if it is missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["ExperimentTracker", "LocalJsonTracker", "MlflowTracker"]


@runtime_checkable
class ExperimentTracker(Protocol):
    def log_params(self, params: Mapping[str, Any]) -> None: ...

    def log_metrics(self, step: int, metrics: Mapping[str, float]) -> None: ...

    def log_artifact(self, path: Path) -> None: ...

    def finish(self) -> None: ...


class LocalJsonTracker:
    """Writes ``params.json`` and appends to ``metrics.jsonl`` inside ``run_dir``."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: list[str] = []

    def log_params(self, params: Mapping[str, Any]) -> None:
        path = self._run_dir / "params.json"
        payload = json.dumps(dict(params), indent=2, sort_keys=True, default=str)
        path.write_text(payload, encoding="utf-8")

    def log_metrics(self, step: int, metrics: Mapping[str, float]) -> None:
        path = self._run_dir / "metrics.jsonl"
        record = {"step": step, **dict(metrics)}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    def log_artifact(self, path: Path) -> None:
        self._artifacts.append(str(path))
        manifest = self._run_dir / "artifacts.json"
        manifest.write_text(json.dumps(self._artifacts, indent=2), encoding="utf-8")

    def finish(self) -> None:
        return None


class MlflowTracker:
    """Thin wrapper over the ``mlflow`` client, imported lazily at construction time."""

    def __init__(self, tracking_uri: str, run_name: str | None = None) -> None:
        try:
            import mlflow  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "tracking.backend=mlflow requires the mlflow package; install it "
                "separately (it is not part of forecheck[train])"
            ) from exc
        mlflow.set_tracking_uri(tracking_uri)
        self._mlflow = mlflow
        self._run = mlflow.start_run(run_name=run_name)

    def log_params(self, params: Mapping[str, Any]) -> None:
        self._mlflow.log_params(dict(params))

    def log_metrics(self, step: int, metrics: Mapping[str, float]) -> None:
        self._mlflow.log_metrics(dict(metrics), step=step)

    def log_artifact(self, path: Path) -> None:
        self._mlflow.log_artifact(str(path))

    def finish(self) -> None:
        self._mlflow.end_run()
