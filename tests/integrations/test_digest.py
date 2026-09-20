from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from forecheck.integrations.digest import argument_digest, canonical_json

_JSON_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**9), max_value=10**9),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=20),
)


@st.composite
def _json_dicts(draw: st.DrawFn) -> dict[str, object]:
    return draw(st.dictionaries(st.text(min_size=1, max_size=10), _JSON_SCALARS, max_size=8))


@given(_json_dicts())
def test_key_order_does_not_affect_digest(mapping: dict[str, object]) -> None:
    reordered = dict(reversed(list(mapping.items())))
    assert argument_digest(mapping) == argument_digest(reordered)


@given(_json_dicts())
def test_digest_is_deterministic(mapping: dict[str, object]) -> None:
    assert argument_digest(mapping) == argument_digest(dict(mapping))


def test_differing_value_changes_digest() -> None:
    assert argument_digest({"a": 1}) != argument_digest({"a": 2})


def test_differing_key_changes_digest() -> None:
    assert argument_digest({"a": 1}) != argument_digest({"b": 1})


def test_nan_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        argument_digest({"a": math.nan})


def test_infinity_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        argument_digest({"a": math.inf})


def test_bytes_are_base64_normalised() -> None:
    digest = argument_digest({"payload": b"hello"})
    assert digest == argument_digest({"payload": b"hello"})
    assert digest != argument_digest({"payload": b"hellp"})


def test_datetime_becomes_isoformat() -> None:
    when = datetime(2026, 1, 1, tzinfo=UTC)
    payload = canonical_json({"at": when})
    assert when.isoformat() in payload


def test_nested_structures_are_canonicalised() -> None:
    a = {"outer": {"z": 1, "a": 2}, "list": [1, 2, {"y": 1, "x": 2}]}
    b = {"list": [1, 2, {"x": 2, "y": 1}], "outer": {"a": 2, "z": 1}}
    assert argument_digest(a) == argument_digest(b)


def test_unsupported_type_raises() -> None:
    class Unsupported:
        pass

    with pytest.raises(TypeError):
        argument_digest({"a": Unsupported()})
