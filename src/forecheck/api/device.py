"""CPU / CUDA / MPS capability detection, surfaced on ``GET /version``.

Torch is imported lazily so this module -- and everything that imports it -- works in
environments where the ``torch`` extra is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["DeviceInfo", "detect"]

DeviceKind = Literal["cpu", "cuda", "mps"]


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    kind: DeviceKind
    name: str | None
    bf16_supported: bool
    memory_gb: float | None
    torch_available: bool


def detect() -> DeviceInfo:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return DeviceInfo(
            kind="cpu", name=None, bf16_supported=False, memory_gb=None, torch_available=False
        )

    if torch.cuda.is_available():
        index = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(index)
        is_bf16 = getattr(torch.cuda, "is_bf16_supported", None)
        return DeviceInfo(
            kind="cuda",
            name=str(props.name),
            bf16_supported=bool(is_bf16()) if is_bf16 is not None else False,
            memory_gb=float(props.total_memory) / (1024**3),
            torch_available=True,
        )

    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return DeviceInfo(
            kind="mps",
            name="Apple Silicon",
            bf16_supported=True,
            memory_gb=None,
            torch_available=True,
        )

    return DeviceInfo(
        kind="cpu", name=None, bf16_supported=False, memory_gb=None, torch_available=True
    )
