"""Unit tests for :func:`src.ingestion.parsers.red_blocks.extract_red_blocks`.

Red blocks are ``td_vermelha`` cells on a schedule grid marking a teacher or
room as unavailable. The parser maps each to a ``(time, weekday)`` pair by
locating the cell's column (via the expanded matrix) and its row's time label.
"""

import pytest
from bs4 import BeautifulSoup

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
