import sqlite3
from collections.abc import Sequence
from typing import cast

from bs4 import Tag

from src.ingestion.schemas import Matrix


def pre_insert_red_blocks(
    cursor: sqlite3.Cursor,
    conn: sqlite3.Connection,
) -> None:
    """
    Pre-populates the red blocks table at the start of parsing.

    The red blocks table, used for database lookups, is filled with all
    possible unavailability time slots that may appear in the remaining
    schedules. Time slots range from 08:00 to 22:00 in 30-minute intervals,
    for each weekday (Monday through Saturday).
    """
    for dia in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]:
        # Time slots from 08:00 to 22:00 in 100-minute steps
        for hora in range(800, 2201, 100):
            for minuto in [0, 30]:  # Minutes 0 and 30
                horario = hora + minuto
                stmt = """INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)"""
                cursor.execute(stmt, (horario, dia))
                conn.commit()


def matrix_from_html_table(table: Tag) -> Matrix:
    """Convert an HTML table element into a 2D matrix.

    Cells with rowspan/colspan are repeated across all the rows and columns
    they occupy, making it straightforward to map schedule times and durations
    by position.

    Args:
        table: A BeautifulSoup Tag representing a <table> element. The first
            three rows are treated as headers and skipped.

    Returns:
        A 2D list where each entry is the <td> Tag that visually occupies
        that (row, col) position, accounting for rowspan and colspan.
    """
    rows = table.find_all("tr")[3:]

    num_rows = len(rows)
    num_cols = max(len(row.find_all(["td", "th"])) for row in rows)

    matrix: list[list[Tag | None]] = [[None] * num_cols for _ in range(num_rows)]

    for i, row in enumerate(rows):
        j = 0
        for cell in row.find_all("td"):
            rowspan = int(str(cell.get("rowspan") or 1))
            colspan = int(str(cell.get("colspan") or 1))

            while matrix[i][j] is not None:
                j += 1

            for k in range(rowspan):
                for m in range(colspan):
                    matrix[i + k][j + m] = cell

            j += colspan

    if not all(cell for row in matrix[1:] for cell in row):
        raise ValueError("Matrix has unfilled cells — table structure may be malformed")

    return cast(Sequence[Sequence[Tag]], matrix)


def get_cell_column(item: Tag, matrix: Matrix) -> int:
    """Find the column index of a cell in the matrix.

    Args:
        item: The <td> Tag to locate.
        matrix: The 2D matrix returned by ``matrix_from_html_table``.

    Returns:
        The leftmost column index the cell occupies.

    Raises:
        ValueError: If the item is not found in the matrix.
    """
    for row in matrix:
        for j, td in enumerate(row):
            if item == td:
                return j

    raise ValueError("Item not found in matrix")
