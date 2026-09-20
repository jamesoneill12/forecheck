"""Save/load a :class:`CalibratorBundle` as JSON, separately from model weights.

Each artifact carries a ``.sha256`` sidecar so transport corruption is detected before
the bundle is trusted, and loading refuses a bundle whose ``label_schema_version``
does not match the schema this build of forecheck understands.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from forecheck.calibration.base import CalibratorBundle
from forecheck.contracts import LABEL_SCHEMA_VERSION

__all__ = ["load_bundle", "save_bundle"]


def _sidecar_path(path: Path) -> Path:
    return path.with_name(path.name + ".sha256")


def save_bundle(bundle: CalibratorBundle, path: Path) -> None:
    payload = bundle.model_dump_json(indent=2)
    path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    _sidecar_path(path).write_text(f"{digest}  {path.name}\n", encoding="utf-8")


def load_bundle(path: Path) -> CalibratorBundle:
    payload = path.read_text(encoding="utf-8")
    sidecar = _sidecar_path(path)
    if sidecar.exists():
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if actual != expected:
            raise ValueError(f"calibration bundle at {path} failed sha256 verification")
    bundle = CalibratorBundle.model_validate_json(payload)
    if bundle.label_schema_version != LABEL_SCHEMA_VERSION:
        raise ValueError(
            f"calibration bundle label_schema_version {bundle.label_schema_version!r} "
            f"does not match the running schema {LABEL_SCHEMA_VERSION!r}"
        )
    return bundle
