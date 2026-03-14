from collections.abc import Sequence
from typing import cast

from bs4 import Tag

from src.ingestion.schemas.misc import Matrix, WeekDay


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

    Raises:
        ValueError: If any cell in rows after the first is unfilled, indicating
            a malformed table structure.
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


def get_weekday_at_column(column: int, span_map: dict[WeekDay, int]) -> WeekDay:
    """Map a table column index to its corresponding weekday.

    The schedule table has a header row where each weekday spans one or more
    columns (via ``colspan``). This function accumulates those spans to determine
    which weekday owns the given column index.

    Args:
        column: 0-based column index in the schedule matrix, where index 0
            is the time-label column and weekday columns start at index 1.
        span_map: Ordered mapping of each weekday to its colspan width,
            as built from the day-header row.

    Returns:
        The ``WeekDay`` that owns the given column.

    Raises:
        ValueError: If ``column`` exceeds the total span of all weekdays.
    """
    if column == 1:
        return WeekDay.MONDAY

    count = 0
    for day, span in span_map.items():
        count += int(span)
        if count >= column:
            return day

    raise ValueError(
        f"Column index {column} is out of range for the given weekday span map",
    )
