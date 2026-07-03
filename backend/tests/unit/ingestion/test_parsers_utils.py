"""Unit tests for :mod:`src.ingestion.parsers.utils`.

Covers the three low-level table helpers the higher parsers depend on:

* ``matrix_from_html_table`` — expands an HTML ``<table>`` (minus its first
  three header rows) into a dense 2D grid, repeating rowspan/colspan cells.
* ``get_cell_column`` — locates a cell's leftmost column in that grid.
* ``get_weekday_at_column`` — maps a column index to a weekday using the
  colspan widths of the day-header row.
"""

import pytest
from bs4 import BeautifulSoup

from src.ingestion.parsers.utils import (
    get_cell_column,
    get_weekday_at_column,
    matrix_from_html_table,
)
from src.ingestion.schemas.misc import WeekDay


def _table(data_rows: str) -> BeautifulSoup:
    """Wrap ``data_rows`` under three skipped header rows and parse the table."""
    header = "<tr><td>h0</td></tr><tr><td>h1</td></tr><tr><td>h2</td></tr>"
    html = f"<table>{header}{data_rows}</table>"
    return BeautifulSoup(html, "html.parser").find("table")


# ---------------------------------------------------------------------------
# -- matrix_from_html_table
# ---------------------------------------------------------------------------


def test_matrix_skips_first_three_rows() -> None:
    """Only rows after the first three header rows appear in the matrix."""
    table = _table("<tr><td>A</td><td>B</td></tr>")
    matrix = matrix_from_html_table(table)

    assert len(matrix) == 1
    assert [cell.get_text() for cell in matrix[0]] == ["A", "B"]


def test_matrix_expands_colspan_across_columns() -> None:
    """A ``colspan`` cell is repeated across each column it visually occupies."""
    table = _table(
        '<tr><td>x</td><td>y</td></tr><tr><td colspan="2">wide</td></tr>',
    )
    matrix = matrix_from_html_table(table)

    # Row 1 (the colspan row) must be fully filled by the same tag.
    assert matrix[1][0] is matrix[1][1]
    assert matrix[1][0].get_text() == "wide"


def test_matrix_expands_rowspan_down_columns() -> None:
    """A ``rowspan`` cell is repeated down each row it visually occupies."""
    table = _table(
        "<tr><td>t0</td><td>head</td></tr>"
        '<tr><td>t1</td><td rowspan="2">tall</td></tr>'
        "<tr><td>t2</td></tr>",
    )
    matrix = matrix_from_html_table(table)

    # The rowspan cell occupies (row1,col1) and (row2,col1) — same tag object.
    assert matrix[1][1] is matrix[2][1]
    assert matrix[1][1].get_text() == "tall"
    # The trailing row only declared its time cell; the span filled the rest.
    assert matrix[2][0].get_text() == "t2"


def test_matrix_allows_unfilled_cells_in_first_row_only() -> None:
    """The header (row 0) may be ragged; later rows must be dense."""
    # Row 0 has one cell, rows below have two — row 0 keeps a trailing None.
    table = _table(
        "<tr><td>only</td></tr><tr><td>a</td><td>b</td></tr>",
    )
    matrix = matrix_from_html_table(table)

    assert matrix[0][1] is None
    assert matrix[1][0].get_text() == "a"
    assert matrix[1][1].get_text() == "b"


def test_matrix_raises_on_hole_in_later_rows() -> None:
    """A gap in any row after the first is treated as a malformed table."""
    # Row 0 defines two columns; row 1 only fills one, leaving a real hole.
    table = _table(
        "<tr><td>a</td><td>b</td></tr><tr><td>c</td></tr><tr><td>d</td><td>e</td></tr>",
    )
    with pytest.raises(ValueError, match="unfilled cells"):
        matrix_from_html_table(table)


# ---------------------------------------------------------------------------
# -- get_cell_column
# ---------------------------------------------------------------------------


def test_get_cell_column_returns_leftmost_index() -> None:
    table = _table("<tr><td>a</td><td>b</td><td>c</td></tr>")
    matrix = matrix_from_html_table(table)

    assert get_cell_column(matrix[0][0], matrix) == 0
    assert get_cell_column(matrix[0][1], matrix) == 1
    assert get_cell_column(matrix[0][2], matrix) == 2


def test_get_cell_column_colspan_reports_leftmost() -> None:
    table = _table(
        '<tr><td>x</td><td>y</td></tr><tr><td colspan="2">wide</td></tr>',
    )
    matrix = matrix_from_html_table(table)
    wide = matrix[1][0]

    assert get_cell_column(wide, matrix) == 0


def test_get_cell_column_raises_when_absent() -> None:
    table = _table("<tr><td>a</td></tr>")
    matrix = matrix_from_html_table(table)
    stray = BeautifulSoup("<td>stray</td>", "html.parser").find("td")

    with pytest.raises(ValueError, match="Item not found"):
        get_cell_column(stray, matrix)


# ---------------------------------------------------------------------------
# -- get_weekday_at_column
# ---------------------------------------------------------------------------


def test_get_weekday_column_one_is_monday() -> None:
    """Column 1 is special-cased to Monday regardless of the span map."""
    assert get_weekday_at_column(1, {}) is WeekDay.MONDAY


def test_get_weekday_walks_unit_spans() -> None:
    span_map = {
        WeekDay.MONDAY: 1,
        WeekDay.TUESDAY: 1,
        WeekDay.WEDNESDAY: 1,
    }
    assert get_weekday_at_column(2, span_map) is WeekDay.TUESDAY
    assert get_weekday_at_column(3, span_map) is WeekDay.WEDNESDAY


def test_get_weekday_accounts_for_wide_spans() -> None:
    """A weekday spanning several columns owns every column it covers."""
    span_map = {
        WeekDay.MONDAY: 2,  # columns 1..2
        WeekDay.TUESDAY: 3,  # columns 3..5
    }
    assert get_weekday_at_column(2, span_map) is WeekDay.MONDAY
    assert get_weekday_at_column(3, span_map) is WeekDay.TUESDAY
    assert get_weekday_at_column(5, span_map) is WeekDay.TUESDAY


def test_get_weekday_out_of_range_raises() -> None:
    span_map = {WeekDay.MONDAY: 1, WeekDay.TUESDAY: 1}
    with pytest.raises(ValueError, match="out of range"):
        get_weekday_at_column(9, span_map)
