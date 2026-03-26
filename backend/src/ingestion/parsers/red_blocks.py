from bs4 import BeautifulSoup

from src.ingestion.parsers.utils import (
    get_weekday_at_column,
    matrix_from_html_table,
)
from src.ingestion.schemas.misc import RedBlock, WeekDay


def extract_red_blocks(soup: BeautifulSoup) -> list[RedBlock]:
    """Extract unavailable time slots from a schedule page.

    Red blocks (``td_vermelha``) represent time slots where a teacher or
    room is unavailable. The function reads the day-span header to map column
    positions to weekday names, then builds a matrix of the main schedule
    table to locate each red cell's column and derive its weekday.

    Args:
        soup: Parsed HTML of a schedule page.

    Returns:
        A list of ``(time, day)`` tuples, e.g. ``(900, "Segunda")``,
        one entry per red block. Returns an empty list if none are found.

    Raises:
        ValueError: If expected structural elements are missing from the page.
    """
    red_cells = soup.find_all("td", {"class": "td_vermelha"})
    if not red_cells:
        return []

    # -- Build table matrix ------------------------------------------------
    center_element = soup.find("center")
    if center_element is None:
        raise ValueError("Could not find <center> element in section page")

    main_table = center_element.find("table", {"class": "tabela_principal"})
    if main_table is None:
        raise ValueError("Could not find 'tabela_principal' table in section page")

    matrix = matrix_from_html_table(main_table)

    # -- Build week day <-> table width dict -------------------------------
    table_rows = main_table.find_all("tr", recursive=False)
    if len(table_rows) < 4:
        raise ValueError(
            f"Expected at least 4 rows in 'tabela_principal', found {len(table_rows)}",
        )

    weekday_row = table_rows[3]
    weekday_colspan: dict[WeekDay, int] = {}
    for i, day in enumerate(weekday_row.findChildren()):
        if i == 0:
            continue
        weekday_colspan[WeekDay(day.text)] = int(str(day.get("colspan") or 1))

    # -- Build cell -> column lookup (O(rows*cols) once, then O(1) per red cell)
    cell_to_column: dict[int, int] = {}
    for row in matrix:
        for j, td in enumerate(row):
            td_id = id(td)
            if td_id not in cell_to_column:
                cell_to_column[td_id] = j

    # -- Parse red blocks --------------------------------------------------
    result: list[RedBlock] = []
    for item in red_cells:
        table_row = item.parent
        if table_row is None:
            raise ValueError("Red block <td> has no parent")

        column = cell_to_column.get(id(item))
        if column is None:
            raise ValueError("Item not found in matrix")

        first_child = table_row.find()
        if first_child is None:
            raise ValueError("Red block row has no children")

        time = int(first_child.text.replace(":", ""))
        day = get_weekday_at_column(column, weekday_colspan)
        result.append((time, day))

    return result
