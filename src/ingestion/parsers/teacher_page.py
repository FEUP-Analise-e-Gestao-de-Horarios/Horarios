from bs4 import BeautifulSoup

from src.ingestion.schemas.teachers import TeacherPage, TeacherPages


def extract_teacher_info(soup: BeautifulSoup) -> int:
    """Extract teacher acronym, name, and code from a parsed teacher page.

    Parses the `<td class="cabtitulo">` element, which contains the teacher's
    acronym, full name, and numeric code separated by `<br/>` tags.

    Args:
        soup: Parsed HTML of the teacher page.

    Returns:
        A tuple of (acronym, name, code) where:
        - acronym: Short identifier for the teacher (e.g. "ABC").
        - name: Full name, cleaned of punctuation. Falls back to acronym if empty.
        - code: Numeric string identifying the teacher.

    Raises:
        ValueError: If `<td class="cabtitulo">` is not found in the page.
    """
    td = soup.find("td", {"class": "cabtitulo"})
    if td is None:
        raise ValueError("Could not find <td class='cabtitulo'>")

    content = str(td.contents)
    if '"' in content:
        code = int(content.split("<br/>, '")[2].split("'")[0])
    else:
        content = content.split("', <br/>, '")
        code = int(content[2].split("'")[0])

    return code


def extract_teacher_class_page(soup: BeautifulSoup) -> TeacherPages:
    """Extract teacher acronym, name, and code from teacher's table in parsed class page.

    Reads the third table on the page (index 2), skipping the first two header
    rows. Each data row must contain exactly three cells formatted as:
    ``{code} - {name}``, ``{acronym}``, ``{code}``.

    Args:
        soup: Parsed HTML of the teacher page.

    Returns:
        A list of ``TeacherPage`` objects with ``code``, ``acronym``, ``name``, and
        ``red_blocks`` fields.

    Raises:
        ValueError: If fewer than 5 tables are found, no data rows exist, a row
            does not have exactly 3 cells, or the acronym cell does not match
            the expected format.
    """
    tables = soup.find_all(class_="tabela_principal")

    if len(tables) < 5:
        raise ValueError(f"Expected at least 5 tables, found {len(tables)}")

    teachers_rows = tables[2].find_all("tr")[2:]

    teachers: TeacherPages = {}

    for teacher_row in teachers_rows:
        cells = [td.get_text(strip=True) for td in teacher_row.find_all("td")]
        if len(cells) != 3:
            raise ValueError(
                f"Expected exactly 3 cells in row, found {len(cells)}: {teacher_row}",
            )

        acronym_and_name, acronym, code = cells[0], cells[1], cells[2]

        if acronym_and_name.find(" - ") != -1:
            print(acronym_and_name)
            _code, name = acronym_and_name.split(" - ", 1)
        else:
            name = acronym_and_name

        code = int(code)

        teacher: TeacherPage = {"code": code, "acronym": acronym, "name": name}
        teachers[code] = teacher

    return teachers
