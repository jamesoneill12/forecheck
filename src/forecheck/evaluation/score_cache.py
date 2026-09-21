"""On-disk cache of raw backend scores for a split, keyed on everything that affects them.

Threshold selection re-scores the selection split on every ``forecheck evaluate``
call. With a decoder backend that is several thousand rows per report, so the cache
lets the second and later reports of a run reuse the first one's dev scores.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from forecheck.contracts.enums import RiskDimension
from forecheck.contracts.io import TruncationInfo
from forecheck.inference.base import RawScores

__all__ = ["load_raw_scores", "save_raw_scores", "score_cache_path"]

_CACHE_FORMAT = 1


def score_cache_path(
    run: Path,
    *,
    split: str,
    dataset_sha256: str,
    model_id: str,
    prompt_contract_hash: str,
    strip_identity: bool,
) -> Path:
    key = hashlib.sha256(
        json.dumps(
            [_CACHE_FORMAT, dataset_sha256, model_id, prompt_contract_hash, strip_identity]
        ).encode("utf-8")
    ).hexdigest()[:16]
    return run / "cache" / f"raw-scores-{split}-{key}.json"


def save_raw_scores(path: Path, raw: Sequence[RawScores]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "scores": {d.value: v for d, v in r.scores.items()},
            "truncation": r.truncation.model_dump(),
            "abstained": sorted(d.value for d in r.abstained_dimensions),
            "prompt_tokens": r.prompt_tokens,
        }
        for r in raw
    ]
    path.write_text(json.dumps({"format": _CACHE_FORMAT, "rows": rows}), encoding="utf-8")


def load_raw_scores(path: Path, expected_rows: int) -> list[RawScores] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if payload.get("format") != _CACHE_FORMAT or not isinstance(rows, list):
        return None
    if len(rows) != expected_rows:
        return None
    return [
        RawScores(
            scores={RiskDimension(k): float(v) for k, v in row["scores"].items()},
            truncation=TruncationInfo.model_validate(row["truncation"]),
            abstained_dimensions=frozenset(RiskDimension(d) for d in row["abstained"]),
            prompt_tokens=row.get("prompt_tokens"),
        )
        for row in rows
    ]
