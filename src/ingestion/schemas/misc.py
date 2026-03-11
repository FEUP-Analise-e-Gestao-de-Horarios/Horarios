from collections.abc import Sequence
from enum import StrEnum

from bs4 import Tag

Matrix = Sequence[Sequence[Tag]]
"""A 2D grid of BeautifulSoup ``Tag`` objects representing an HTML table.

Each cell holds the ``<td>`` tag that visually occupies that (row, col)
position. Cells spanning multiple rows or columns via ``rowspan``/``colspan``
are repeated across every position they cover, so any (row, col) lookup
directly yields the tag responsible for that slot — no span arithmetic needed.

The first three rows of the source table (treated as headers) are excluded.

See Also:
    :func:`src.ingestion.parsers.utils.matrix_from_html_table` — the function
    that produces this type.
"""


Time = int
"""An integer encoding of a schedule time as ``HHMM``.

Examples:
    - ``1000`` → 10:00
    - ``1230`` → 12:30
"""


class WeekDay(StrEnum):
    """Days of the week, with Portuguese values for compatibility with external services."""

    MONDAY = "Segunda"
    TUESDAY = "Terça"
    WEDNESDAY = "Quarta"
    THURSDAY = "Quinta"
    FRIDAY = "Sexta"
    SATURDAY = "Sábado"

    @classmethod
    def _missing_(cls, value: object) -> WeekDay:
        """Look up a ``WeekDay`` by a case-insensitive English or Portuguese name.

        Args:
            value: The raw value passed to ``WeekDay()``.

        Returns:
            The matching ``WeekDay`` member.

        Raises:
            ValueError: If ``value`` is not a string or does not match any
                known alias.
        """
        if not isinstance(value, str):
            raise ValueError(f"{value!r} is not a valid WeekDay")

        normalized = value.strip().lower()
        aliases: dict[str, WeekDay] = {
            "monday": cls.MONDAY,
            "segunda": cls.MONDAY,
            "tuesday": cls.TUESDAY,
            "terça": cls.TUESDAY,
            "terca": cls.TUESDAY,
            "wednesday": cls.WEDNESDAY,
            "quarta": cls.WEDNESDAY,
            "thursday": cls.THURSDAY,
            "quinta": cls.THURSDAY,
            "friday": cls.FRIDAY,
            "sexta": cls.FRIDAY,
            "saturday": cls.SATURDAY,
            "sábado": cls.SATURDAY,
            "sabado": cls.SATURDAY,
        }

        if normalized not in aliases:
            raise ValueError(f"{value!r} is not a valid WeekDay")

        return aliases[normalized]


RedBlock = tuple[Time, WeekDay]
"""A single unavailable time slot in a teacher's or room's schedule.

Represented as a ``(time, day)`` pair extracted from cells marked with the
``td_vermelha`` CSS class in the institution's schedule pages.

Fields:
    - ``time`` (:data:`Time`): Start time encoded as ``HHMM``
      (e.g. ``900`` for 09:00, ``1230`` for 12:30).
    - ``day`` (:class:`WeekDay`): The day of the week on which the slot falls.

Example:
    ``(900, WeekDay.MONDAY)`` — unavailable on Monday at 09:00.

See Also:
    :func:`src.ingestion.parsers.red_blocks.extract_red_blocks` — the function
    that produces this type.
"""
