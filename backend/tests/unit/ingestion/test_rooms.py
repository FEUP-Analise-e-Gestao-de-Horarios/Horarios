"""Unit tests for :mod:`src.ingestion.rooms`.

``ROOMS`` is a static data registry (room code -> ``{type, size, seats}``)
consumed by :func:`src.ingestion.parsers.menu.extract_rooms_info`. It has no
behaviour of its own, so these tests are structural guards against copy-paste
or typo errors in the ~110-row table:

* every value is a dict with exactly the keys ``{"type", "size", "seats"}``;
* every field value is a ``str``;
* the ``type`` categories are exactly the four documented ones
  (``Anf``, ``PCs``, ``TPs``, ``Redes``) — no stray/typo category.
"""

import pytest

from src.ingestion.rooms import ROOMS

# The four documented room categories (see the ROOMS docstring).
VALID_TYPES = {"Anf", "PCs", "TPs", "Redes"}

# Expected key set for every registry value.
EXPECTED_KEYS = {"type", "size", "seats"}


# ---------------------------------------------------------------------------
# -- per-entry shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("code", "meta"), sorted(ROOMS.items()))
def test_rooms_entry_has_exactly_the_three_string_fields(
    code: str,
    meta: dict[str, str],
) -> None:
    """Each entry has exactly {type,size,seats}, all non-empty strings."""
    assert isinstance(code, str)
    assert set(meta.keys()) == EXPECTED_KEYS
    for field, value in meta.items():
        assert isinstance(value, str), f"{code}.{field} is not a str"
        assert value != "", f"{code}.{field} is empty"


@pytest.mark.parametrize(("code", "meta"), sorted(ROOMS.items()))
def test_rooms_entry_type_is_a_known_category(
    code: str,
    meta: dict[str, str],
) -> None:
    """Every ``type`` is one of the four documented categories."""
    assert meta["type"] in VALID_TYPES, f"{code} has unexpected type {meta['type']!r}"


# ---------------------------------------------------------------------------
# -- registry-wide invariants
# ---------------------------------------------------------------------------


def test_rooms_type_categories_are_exactly_the_documented_four() -> None:
    """No accidental extra/typo category, and all four are actually used."""
    assert {meta["type"] for meta in ROOMS.values()} == VALID_TYPES


def test_rooms_type_distribution_is_exact() -> None:
    """Lock in the exact per-category row counts (total 99 rooms)."""
    counts: dict[str, int] = {}
    for meta in ROOMS.values():
        counts[meta["type"]] = counts.get(meta["type"], 0) + 1

    assert counts == {"Anf": 34, "PCs": 28, "TPs": 35, "Redes": 2}
    assert len(ROOMS) == 99
    assert sum(counts.values()) == len(ROOMS)


def test_rooms_codes_are_unique_and_upper_alphanumeric() -> None:
    """Room codes are distinct, non-empty, upper-case alphanumeric strings."""
    codes = list(ROOMS.keys())
    assert len(codes) == len(set(codes))
    for code in codes:
        assert code, "empty room code"
        assert code.isalnum(), f"{code!r} is not alphanumeric"
        assert code == code.upper(), f"{code!r} is not upper-case"
