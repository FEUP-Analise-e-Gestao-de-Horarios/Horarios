"""Unit tests for :class:`WeekDay` (English + Portuguese alias resolution).

Pure logic: no database, no HTTP. This file owns all ``WeekDay`` coverage.

Canonical lowercase English values (``"monday"``..``"saturday"``) resolve
directly via the ``StrEnum`` value lookup *before* ``_missing_`` is ever
consulted; every other accepted spelling (English case variants, Portuguese
names accented/folded, surrounding whitespace) flows through ``_missing_``.
There is no Sunday member or alias, so ``"sunday"``/``"domingo"`` raise. Passing
a non-string hits the ``isinstance`` guard and raises ``ValueError`` (never
``TypeError``/``AttributeError``), and the error message repr's the *original*,
un-stripped value.
"""

from pydantic import BaseModel, ValidationError
from pytest import mark, raises

from src.projects.projects_db.schemas.weekday import WeekDay

# Every accepted spelling -> the member it must resolve to.
_EN_CANONICAL = [
    ("monday", WeekDay.MONDAY),
    ("tuesday", WeekDay.TUESDAY),
    ("wednesday", WeekDay.WEDNESDAY),
    ("thursday", WeekDay.THURSDAY),
    ("friday", WeekDay.FRIDAY),
    ("saturday", WeekDay.SATURDAY),
]

_EN_CASE_VARIANTS = [
    ("MONDAY", WeekDay.MONDAY),
    ("Monday", WeekDay.MONDAY),
    ("TuEsDaY", WeekDay.TUESDAY),
    ("Wednesday", WeekDay.WEDNESDAY),
    ("THURSDAY", WeekDay.THURSDAY),
    ("Friday", WeekDay.FRIDAY),
    ("SATURDAY", WeekDay.SATURDAY),
]

_PT_ALIASES = [
    ("segunda", WeekDay.MONDAY),
    ("terça", WeekDay.TUESDAY),
    ("terca", WeekDay.TUESDAY),
    ("quarta", WeekDay.WEDNESDAY),
    ("quinta", WeekDay.THURSDAY),
    ("sexta", WeekDay.FRIDAY),
    ("sábado", WeekDay.SATURDAY),
    ("sabado", WeekDay.SATURDAY),
    ("SEGUNDA", WeekDay.MONDAY),
    ("Terça", WeekDay.TUESDAY),
    ("SÁBADO", WeekDay.SATURDAY),
]

_WHITESPACE = [
    ("  quarta  ", WeekDay.WEDNESDAY),
    ("\tmonday\n", WeekDay.MONDAY),
    (" Sexta ", WeekDay.FRIDAY),
]

# Unknown *string* names: valid type, no matching alias -> ValueError.
_INVALID_NAMES = ["sunday", "domingo", "funday", "mondayy", "", "   ", "mon"]

# Non-string inputs: caught by the ``isinstance`` guard -> ValueError.
_NON_STRINGS = [1, None, ["monday"], object()]


@mark.parametrize(("value", "expected"), _EN_CANONICAL)
def test_canonical_lowercase_english(value: str, expected: WeekDay) -> None:
    """Canonical lowercase names return the matching member and keep ``.value``."""
    result = WeekDay(value)

    assert result is expected
    assert result.value == value
    # ``StrEnum`` members compare equal to their string value.
    assert result == value


@mark.parametrize(("value", "expected"), _EN_CASE_VARIANTS)
def test_english_case_insensitive(value: str, expected: WeekDay) -> None:
    """English names resolve regardless of case via ``_missing_``."""
    result = WeekDay(value)

    assert result is expected
    # Non-canonical spelling is normalized to the canonical lowercase value.
    assert result.value == expected.value


@mark.parametrize(("value", "expected"), _PT_ALIASES)
def test_portuguese_aliases(value: str, expected: WeekDay) -> None:
    """Portuguese names (accented, folded, any case) map to the right member."""
    result = WeekDay(value)

    assert result is expected
    assert result.value == expected.value


@mark.parametrize(("value", "expected"), _WHITESPACE)
def test_strips_surrounding_whitespace(value: str, expected: WeekDay) -> None:
    """Surrounding whitespace is stripped before alias lookup."""
    result = WeekDay(value)

    assert result is expected


@mark.parametrize("value", _INVALID_NAMES)
def test_unknown_string_raises_value_error(value: str) -> None:
    """Unknown names (incl. 'sunday'/'domingo') raise ``ValueError``."""
    with raises(ValueError, match="is not a valid WeekDay"):
        WeekDay(value)


@mark.parametrize("value", _INVALID_NAMES)
def test_error_message_uses_unstripped_value_repr(value: str) -> None:
    """The message repr's the original (un-stripped) value."""
    with raises(ValueError) as exc_info:
        WeekDay(value)

    assert str(exc_info.value) == f"{value!r} is not a valid WeekDay"


def test_error_message_keeps_whitespace_in_repr() -> None:
    """A whitespace-padded unknown value keeps its padding in the repr."""
    with raises(ValueError) as exc_info:
        WeekDay("  domingo  ")

    assert str(exc_info.value) == "'  domingo  ' is not a valid WeekDay"


@mark.parametrize("value", _NON_STRINGS)
def test_non_string_raises_value_error_not_type_error(value: object) -> None:
    """Non-string input hits the isinstance guard -> ``ValueError`` only."""
    with raises(ValueError, match="is not a valid WeekDay") as exc_info:
        WeekDay(value)

    # Regression guard: the guard must fire before ``.strip()`` is reached, so
    # no ``AttributeError``/``TypeError`` escapes as the raised exception.
    assert type(exc_info.value) is ValueError
    assert str(exc_info.value) == f"{value!r} is not a valid WeekDay"


class _WeekDayModel(BaseModel):
    """Local model exercising ``WeekDay`` as a pydantic field."""

    weekday: WeekDay


@mark.parametrize(
    ("value", "expected"),
    [
        ("segunda", WeekDay.MONDAY),
        ("SÁBADO", WeekDay.SATURDAY),
        ("monday", WeekDay.MONDAY),
        ("TuEsDaY", WeekDay.TUESDAY),
    ],
)
def test_pydantic_field_coerces_aliases(value: str, expected: WeekDay) -> None:
    """A ``WeekDay`` pydantic field coerces EN/PT aliases to the member."""
    model = _WeekDayModel(weekday=value)

    assert model.weekday is expected
    assert model.weekday.value == expected.value


@mark.parametrize("value", ["sunday", "domingo", "funday", ""])
def test_pydantic_field_rejects_invalid(value: str) -> None:
    """Invalid values raise pydantic ``ValidationError`` through the field."""
    with raises(ValidationError):
        _WeekDayModel(weekday=value)
