"""Unit tests for :func:`src.ingestion.parsers.red_blocks.extract_red_blocks`.

Red blocks are ``td_vermelha`` cells on a schedule grid marking a teacher or
room as unavailable. The parser maps each to a ``(time, weekday)`` pair by
locating the cell's column (via the expanded matrix) and its row's time label.
"""

import pytest
from bs4 import BeautifulSoup

from src.ingestion.parsers.class_page import extract_sessions
from src.ingestion.parsers.red_blocks import extract_red_blocks
from src.ingestion.schemas.misc import WeekDay
from tests.unit.ingestion import _html as H


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# -- Happy path
# ---------------------------------------------------------------------------


def test_no_red_cells_returns_empty() -> None:
    """A page with no ``td_vermelha`` cells yields no red blocks (and never
    touches the rest of the page)."""
    assert (
        extract_red_blocks(
            _soup(
                H.room_page(red_time_rows=[[H.time_cell("09:00"), H.empty_cell(), H.empty_cell()]]),
            ),
        )
        == []
    )


def test_single_monday_red_block() -> None:
    page = H.room_page(red_time_rows=[[H.time_cell("09:00"), H.red_cell(), H.empty_cell()]])
    assert extract_red_blocks(_soup(page)) == [(900, WeekDay.MONDAY)]


def test_red_block_resolves_tuesday_column() -> None:
    page = H.room_page(red_time_rows=[[H.time_cell("14:30"), H.empty_cell(), H.red_cell()]])
    assert extract_red_blocks(_soup(page)) == [(1430, WeekDay.TUESDAY)]


def test_multiple_red_blocks_across_rows_and_days() -> None:
    page = H.room_page(
        red_time_rows=[
            [H.time_cell("09:00"), H.red_cell(), H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.red_cell()],
        ],
    )
    assert set(extract_red_blocks(_soup(page))) == {
        (900, WeekDay.MONDAY),
        (1000, WeekDay.TUESDAY),
    }


def test_red_blocks_on_a_class_page() -> None:
    """Class pages carry red blocks in the same main grid as their sessions."""
    page = H.class_page(red_blocks_in_main=True)
    assert extract_red_blocks(_soup(page)) == [(1000, WeekDay.MONDAY)]


# ---------------------------------------------------------------------------
# -- Structural errors
# ---------------------------------------------------------------------------


def test_missing_center_raises() -> None:
    html = '<html><body><table class="tabela_principal">'
    html += '<tr><td class="td_vermelha"></td></tr></table></body></html>'
    with pytest.raises(ValueError, match="center"):
        extract_red_blocks(_soup(html))


def test_missing_main_table_raises() -> None:
    html = '<html><body><center><td class="td_vermelha"></td></center></body></html>'
    with pytest.raises(ValueError, match="tabela_principal"):
        extract_red_blocks(_soup(html))


def test_red_cell_outside_matrix_raises() -> None:
    """A red cell living in the three skipped header rows is not in the matrix."""
    grid = (
        '<table class="tabela_principal">'
        '<tr><td class="td_vermelha">stray</td></tr>'  # header row 0, skipped
        "<tr><td>h1</td></tr><tr><td>h2</td></tr>"
        + H.weekday_header([("Segunda", 1)])
        + "<tr><td>09:00</td><td></td></tr>"
        "</table>"
    )
    html = f"<html><body><center>{grid}</center></body></html>"
    with pytest.raises(ValueError, match="Item not found in matrix"):
        extract_red_blocks(_soup(html))


# ---------------------------------------------------------------------------
# -- Time-label & duration boundary sweep
# ---------------------------------------------------------------------------
#
# Both parsers encode a start time as ``int(label.replace(":", ""))``
# (red_blocks.py:80 / class_page.py:342) and a duration as ``int(rowspan)``
# (class_page.py:345). The pre-existing tests only sampled 09:00/10:00/11:00/
# 14:00/14:30 and rowspan 1/3. The tables below sweep boundary HHMM labels
# through *both* parsers, sweep durations through ``extract_sessions``, and pin
# the garbage-time reject path (a non-numeric label must raise, never silently
# encode a wrong HHMM).

# (label, expected HHMM int) — midnight, single/double-digit hours, half-hours,
# a non-round minute, and the end-of-day boundary.
_TIME_LABELS: list[tuple[str, int]] = [
    ("00:00", 0),
    ("08:00", 800),
    ("09:30", 930),
    ("23:30", 2330),
    ("14:05", 1405),
]

# Labels that are not a valid int after stripping ":" — must raise ValueError
# (from int()) rather than produce a bogus time.
_GARBAGE_TIME_LABELS: list[str] = ["noon", "9h00", "", "12:3o", "1h30", "am"]


def _class_page_one_session(label: str, *, rowspan: int = 1) -> str:
    """A class page carrying exactly one Monday session at ``label`` (rowspan slots).

    Extra filler rows are appended so the ``rowspan`` cell has real rows to
    occupy — the session's own time still comes from its first (row-0) cell.
    """
    first_row = [H.time_cell(label), H.session_cell(rowspan=rowspan), H.empty_cell()]
    # Rows 1..rowspan-1: the session cell already fills the Monday column, so
    # each only needs a time-label cell (col 0) and the Tuesday cell (col 2).
    filler = [[H.time_cell("00:00"), H.empty_cell()] for _ in range(rowspan - 1)]
    return H.class_page(time_rows=[first_row, *filler])


@pytest.mark.parametrize(("label", "expected"), _TIME_LABELS)
def test_red_block_time_label_boundaries(label: str, expected: int) -> None:
    """``extract_red_blocks`` encodes each boundary label as its HHMM int."""
    page = H.room_page(red_time_rows=[[H.time_cell(label), H.red_cell(), H.empty_cell()]])
    assert extract_red_blocks(_soup(page)) == [(expected, WeekDay.MONDAY)]


@pytest.mark.parametrize(("label", "expected"), _TIME_LABELS)
def test_session_start_time_label_boundaries(label: str, expected: int) -> None:
    """``extract_sessions`` encodes each boundary label as its HHMM ``start_time``."""
    sessions = extract_sessions(_soup(_class_page_one_session(label)))
    assert len(sessions) == 1
    assert sessions[0]["start_time"] == expected
    assert sessions[0]["weekday"] == WeekDay.MONDAY
    assert sessions[0]["duration"] == 1


@pytest.mark.parametrize("rowspan", [1, 2, 4])
def test_session_duration_equals_rowspan(rowspan: int) -> None:
    """``extract_sessions`` reads a session's duration straight from its rowspan."""
    sessions = extract_sessions(_soup(_class_page_one_session("09:00", rowspan=rowspan)))
    assert len(sessions) == 1
    assert sessions[0]["duration"] == rowspan
    # Duration must not leak into the (independently parsed) start time.
    assert sessions[0]["start_time"] == 900


@pytest.mark.parametrize("label", _GARBAGE_TIME_LABELS)
def test_red_block_garbage_time_label_raises(label: str) -> None:
    """A non-numeric time label makes ``extract_red_blocks`` raise, not guess."""
    page = H.room_page(red_time_rows=[[H.time_cell(label), H.red_cell(), H.empty_cell()]])
    with pytest.raises(ValueError):
        extract_red_blocks(_soup(page))


@pytest.mark.parametrize("label", _GARBAGE_TIME_LABELS)
def test_session_garbage_time_label_raises(label: str) -> None:
    """A non-numeric time label makes ``extract_sessions`` raise, not guess."""
    with pytest.raises(ValueError):
        extract_sessions(_soup(_class_page_one_session(label)))
