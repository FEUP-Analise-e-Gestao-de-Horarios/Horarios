"""Unit tests for :mod:`src.exporter.export_graph_utils`.

Pure helpers, no database or HTTP. These functions are the shared primitives
the whole exporter graph is built on:

* ``convert_to_minutes`` / ``get_time_slots`` — the ``HHMM``/``HH:MM`` → 30-min
  slot expansion every placement node depends on.
* ``normalize_id`` / ``to_uuid`` — the hyphen-insensitive id forms that let the
  graph compare change keys, snapshot ids and UUID columns interchangeably.
* ``parse_week_date`` — parses a week both before and after JSON serialization.
* ``jsonable`` — the stable, comparable projection used for grouping changes.
"""

import datetime
import uuid

from pytest import mark, raises

from src.exporter.export_graph_utils import (
    convert_to_minutes,
    get_time_slots,
    jsonable,
    normalize_id,
    parse_week_date,
    to_uuid,
)

# ---------------------------------------------------------------------------
# -- convert_to_minutes
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("value", "expected"),
    [
        (830, 510),
        (800, 480),
        (0, 0),
        (2359, 23 * 60 + 59),
        (1000, 600),
        (930, 570),
        ("830", 510),
        ("8:30", 510),
        ("08:30", 510),
        ("0:00", 0),
        ("23:59", 23 * 60 + 59),
        ("9:05", 9 * 60 + 5),
    ],
)
def test_convert_to_minutes_hhmm_and_colon_forms(value: int | str, expected: int) -> None:
    assert convert_to_minutes(value) == expected


def test_convert_to_minutes_colon_form_takes_precedence_over_int_parsing() -> None:
    # A string with a colon is split on ``:``; without it the string is treated
    # as an HHMM integer.
    assert convert_to_minutes("10:15") == 10 * 60 + 15
    assert convert_to_minutes("1015") == 10 * 60 + 15


def test_convert_to_minutes_single_digit_int_is_minutes_only() -> None:
    # 9 -> 9 // 100 * 60 + 9 % 100 == 0 + 9 == 9 (nine minutes past midnight).
    assert convert_to_minutes(9) == 9


# ---------------------------------------------------------------------------
# -- get_time_slots
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("start_time", "duration", "expected"),
    [
        (830, 2, (510, 540)),
        (830, 1, (510,)),
        (830, 0, ()),
        (1000, 3, (600, 630, 660)),
        ("8:30", 2, (510, 540)),
        ("8:30", 4, (510, 540, 570, 600)),
    ],
)
def test_get_time_slots_expands_into_30_minute_steps(
    start_time: int | str,
    duration: int,
    expected: tuple[int, ...],
) -> None:
    assert get_time_slots(start_time, duration) == expected


def test_get_time_slots_accepts_string_duration() -> None:
    # duration is coerced via ``int(duration)``.
    assert get_time_slots(830, "2") == (510, 540)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# -- normalize_id
# ---------------------------------------------------------------------------


def test_normalize_id_strips_hyphens_from_uuid_string() -> None:
    hyphenated = "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3"
    assert normalize_id(hyphenated) == "019e21c08ed57722bd5e8ad5a3c750b3"


def test_normalize_id_of_uuid_object_matches_normalized_string() -> None:
    value = uuid.UUID("019e21c0-8ed5-7722-bd5e-8ad5a3c750b3")
    assert normalize_id(value) == "019e21c08ed57722bd5e8ad5a3c750b3"
    assert normalize_id(value) == normalize_id(str(value))


@mark.parametrize(
    ("value", "expected"),
    [
        ("plain", "plain"),
        (123, "123"),
        ("a-b-c", "abc"),
        (None, "None"),
    ],
)
def test_normalize_id_stringifies_and_removes_hyphens(value: object, expected: str) -> None:
    assert normalize_id(value) == expected  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# -- to_uuid
# ---------------------------------------------------------------------------


def test_to_uuid_returns_same_object_for_uuid_input() -> None:
    value = uuid.uuid7()
    assert to_uuid(value) is value


def test_to_uuid_parses_hyphenated_and_normalized_strings_equally() -> None:
    hyphenated = "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3"
    normalized = "019e21c08ed57722bd5e8ad5a3c750b3"
    assert to_uuid(hyphenated) == to_uuid(normalized)
    assert to_uuid(hyphenated) == uuid.UUID(hyphenated)


def test_to_uuid_rejects_non_uuid_string() -> None:
    with raises(ValueError):
        to_uuid("definitely-not-a-uuid")


# ---------------------------------------------------------------------------
# -- parse_week_date
# ---------------------------------------------------------------------------


def test_parse_week_date_returns_date_unchanged() -> None:
    value = datetime.date(2026, 1, 5)
    assert parse_week_date(value) is value


def test_parse_week_date_parses_iso_string() -> None:
    assert parse_week_date("2026-01-05") == datetime.date(2026, 1, 5)


@mark.parametrize("value", ["not-a-date", "2026-13-99", "", "2026/01/05"])
def test_parse_week_date_returns_none_for_bad_strings(value: str) -> None:
    assert parse_week_date(value) is None


@mark.parametrize("value", [123, None, 12.5, True])
def test_parse_week_date_returns_none_for_non_date_non_str(value: object) -> None:
    assert parse_week_date(value) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# -- jsonable
# ---------------------------------------------------------------------------


def test_jsonable_sorts_dict_keys_recursively_and_stringifies_them() -> None:
    result = jsonable({"b": 1, "a": {"z": 2, "y": 3}})
    assert list(result.keys()) == ["a", "b"]
    assert list(result["a"].keys()) == ["y", "z"]


def test_jsonable_converts_tuples_to_lists() -> None:
    assert jsonable((1, 2, 3)) == [1, 2, 3]
    assert jsonable([1, (2, 3)]) == [1, [2, 3]]


def test_jsonable_keeps_json_scalars_untouched() -> None:
    assert jsonable("x") == "x"
    assert jsonable(7) == 7
    assert jsonable(1.5) == 1.5
    assert jsonable(None) is None
    # bool is a JSON scalar and must not be coerced to a string.
    assert jsonable(True) is True


def test_jsonable_stringifies_non_json_scalars() -> None:
    value = uuid.uuid7()
    assert jsonable(value) == str(value)
    assert jsonable(datetime.date(2026, 1, 5)) == "2026-01-05"


def test_jsonable_non_string_keys_are_stringified_and_sorted_as_strings() -> None:
    result = jsonable({2: "two", 10: "ten", 1: "one"})
    # Keys are compared as strings: "1" < "10" < "2".
    assert list(result.keys()) == ["1", "10", "2"]


def test_jsonable_is_stable_for_equal_but_differently_ordered_dicts() -> None:
    left = jsonable({"start_time": {"new": 1000, "old": 830}, "weekday": "monday"})
    right = jsonable({"weekday": "monday", "start_time": {"old": 830, "new": 1000}})
    assert left == right
    assert str(left) == str(right)
