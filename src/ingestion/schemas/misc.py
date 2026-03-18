from collections.abc import Sequence

from bs4 import Tag

from src.projects.projects_db.schemas.weekday import WeekDay

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


TurnosMap = dict[str, dict[int, dict[str, dict[int, list[str]]]]]
"""Maps each degree and year to its subjects, each with an ordered, sorted collection of shifts.

Structure::

    TurnosMap[degree_acronym][year][subject_code][turno_number] = [class1, class2, ...]

- ``degree_acronym`` (:class:`str`): Degree acronym (e.g. ``"LEI"``).
- ``year`` (:class:`int`): Academic year number (e.g. ``1``, ``2``, ``3``).
- ``subject_code`` (:class:`str`): Institutional subject code (e.g. ``"L.EM009"``).
- ``turno_number`` (:class:`int`): 1-based shift index, assigned in sorted order.
- The list value holds the class codes belonging to that shift.

Example::

    {
        "LEI": {
            1: {
                "L.EM009": {
                    1: ["1LEM01", "1LEM02", "1LEM03"],
                    2: ["1LEM06", "1LEM07", "1LEM08"],
                }
            }
        }
    }

See Also:
    :meth:`src.ingestion.manager.IngestionManager._ingest_shifts` — assigns shift numbers using this structure.
"""
