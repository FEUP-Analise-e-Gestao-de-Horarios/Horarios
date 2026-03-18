import re
from datetime import date

from bs4 import BeautifulSoup

from src.ingestion.parsers.utils import (
    get_cell_column,
    get_weekday_at_column,
    matrix_from_html_table,
)
from src.ingestion.schemas.classes import Session, Subject, Teacher
from src.ingestion.schemas.misc import WeekDay

THEORETICAL_SESSION = "td_tipologia_19"
"""CSS class used by the institution's schedule pages to mark theoretical sessions."""


def extract_week_dates(soup: BeautifulSoup) -> tuple[date, date]:
    """Extract the start and end dates of the schedule week from a section page.

    Locates the ``cabtitulo`` cell, reads its last text node, and extracts the
    two dates using the pattern ``DD/MM/YYYY``.

    Args:
        soup: Parsed HTML of a section schedule page.

    Returns:
        A ``(start_date, end_date)`` tuple of ``date`` objects.

    Raises:
        ValueError: If the ``cabtitulo`` cell is not found or no dates can be
            extracted from its text content.
    """
    weeks_tag = soup.find("td", {"class": "cabtitulo"})
    if weeks_tag is None:
        raise ValueError("Could not find 'cabtitulo' cell in schedule page")

    weeks = str(weeks_tag.contents[-1])
    dates = re.findall(r"\d{2}/\d{2}/\d{4}", weeks)
    if not dates:
        raise ValueError(f"Could not find dates in weeks string: {weeks!r}")

    start_date = date.strptime(dates[0], "%d/%m/%Y")
    end_date = date.strptime(dates[-1], "%d/%m/%Y")
    return start_date, end_date


def extract_teachers(soup: BeautifulSoup) -> list[Teacher]:
    """Extract the list of teachers from a class schedule page.

    Reads the third ``tabela_principal`` table (index 2), skipping the first
    two header rows. Each data row must contain exactly three cells: a combined
    ``{code} - {name}`` string, the teacher's acronym, and a numeric code.

    Args:
        soup: Parsed HTML of a class schedule page.

    Returns:
        A list of ``Teacher`` dicts with ``code``, ``acronym``, and ``name`` fields.

    Raises:
        ValueError: If fewer than 5 ``tabela_principal`` tables are found or
            a row does not have exactly 3 cells.
    """
    tables = soup.find_all(class_="tabela_principal")

    if len(tables) < 5:
        raise ValueError(f"Expected at least 5 tables, found {len(tables)}")

    teachers_rows = tables[2].find_all("tr")[2:]

    teachers: list[Teacher] = []

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

        teachers.append({"code": int(code), "acronym": acronym, "name": name})

    return teachers


def extract_subjects(soup: BeautifulSoup) -> list[Subject]:
    """Extract the list of subjects associated with a section from a section page.

    Reads the fifth table on the page (index 4), skipping the first two header
    rows. Each data row must contain exactly three cells formatted as:
    ``{code} - {name}``, ``{acronym}({year} - {number})``, and a student count.

    Args:
        soup: Parsed HTML of a section schedule page.

    Returns:
        A list of ``Subject`` objects with ``code``, ``name``, ``acronym``, and
        ``number`` (student count) fields.

    Raises:
        ValueError: If fewer than 5 tables are found, no data rows exist, a row
            does not have exactly 3 cells, or the acronym cell does not match
            the expected format.
    """
    all_tables = soup.find_all("table")
    if len(all_tables) < 5:
        raise ValueError(f"Expected at least 5 tables, found {len(all_tables)}")

    subjects_rows = all_tables[4].find_all("tr")[2:]
    if not subjects_rows:
        raise ValueError("No subjects rows found in the subjects table")

    subjects: list[Subject] = []
    for row in subjects_rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) != 3:
            raise ValueError(
                f"Expected exactly 3 cells in row, found {len(cells)}: {row}",
            )

        code_and_name, raw_acronym, number = cells[0], cells[1], cells[2]
        code, name = code_and_name.split(" - ", 1)
        number = int(number)

        acronym_match = re.fullmatch(r"(.+)\((\d{4}) ?- ?(\d+)\)", raw_acronym)
        if not acronym_match:
            raise ValueError(f"Unexpected acronym format: {raw_acronym!r}")
        acronym = acronym_match.group(1).strip()

        subjects.append(
            {
                "code": code,
                "name": name,
                "acronym": acronym,
                "number": number,
            },
        )

    return subjects


def extract_sessions(soup: BeautifulSoup) -> list[Session]:
    """Extract all scheduled sessions from a class page.

    Locates every ``td_tipologia_*`` cell in the main timetable, builds a cell
    position matrix to derive each session's weekday, and reads the teachers
    table (index 3) to resolve teacher acronyms to numeric codes. For each
    session block the function extracts: subject acronym, weekday, start time,
    duration (rowspan), teacher codes, class codes, room, and whether it is a
    theoretical session (CSS class ``td_tipologia_19``).

    Args:
        soup: Parsed HTML of a section schedule page.

    Returns:
        A list of ``Session`` objects. Returns an empty list if no session
        blocks are found on the page.

    Raises:
        ValueError: If required structural elements are missing (``<center>``,
            ``tabela_principal``, teacher rows), a session block has an
            unexpected format, or a teacher acronym is unknown or duplicated.
    """
    center_element = soup.find("center")
    if center_element is None:
        raise ValueError("Could not find <center> element in section page")

    # -- Get session blocks and exit early ---------------------------------
    session_blocks = center_element.find_all("td", class_=re.compile(r"^td_tipologia_"))
    if not session_blocks:
        return []

    # -- Build table matrix ------------------------------------------------
    center_element = soup.find("center")
    if center_element is None:
        raise ValueError("Could not find <center> element in section page")

    main_table = center_element.find("table", {"class": "tabela_principal"})
    if main_table is None:
        raise ValueError("Could not find 'tabela_principal' table in section page")

    matrix = matrix_from_html_table(main_table)

    # -- Build day-span mapping --------------------------------------------
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

    # -- Build teacher abbreviation → code list mapping --------------------
    all_tables = soup.find_all("table")
    if len(all_tables) < 4:
        raise ValueError(f"Expected at least 4 tables, found {len(all_tables)}")

    teachers_table = all_tables[3]
    teachers_rows = teachers_table.find_all("tr")[2:]
    if not teachers_rows:
        raise ValueError("No teacher rows found in teachers table")

    teachers_map: dict[str, int] = {}
    for row in teachers_rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) != 3:
            raise ValueError(
                f"Expected exactly 3 cells in row, found {len(cells)}: {row}",
            )

        acronym, code = cells[1], int(cells[2])
        if acronym in teachers_map:
            raise ValueError(f"Duplicate teacher acronym {acronym!r} in teachers table")
        teachers_map[acronym] = code

    # -- Parse sessions ----------------------------------------------------
    sessions: list[Session] = []
    for session_block in session_blocks:
        # -- Subject Acronym ---------------------------------------------------
        raw_acronym = str(session_block.contents[0]).strip()
        acronym_match = re.fullmatch(r"(.+)\((\d{4}) ?- ?(\d+)\)", raw_acronym)
        if not acronym_match:
            raise ValueError(f"Unexpected acronym format: {raw_acronym!r}")

        subject_acronym_raw = acronym_match.group(1)
        if not isinstance(subject_acronym_raw, str):
            raise ValueError(
                f"Expected string for subject acronym, got {type(subject_acronym_raw)}: {subject_acronym_raw!r}",
            )

        subject_acronym = subject_acronym_raw.strip()
        if not subject_acronym:
            raise ValueError(f"Empty subject acronym in: {raw_acronym!r}")

        # -- Weekday -----------------------------------------------------------
        session_column = get_cell_column(session_block, matrix)
        session_weekday = get_weekday_at_column(session_column, weekday_colspan)

        # -- Start time --------------------------------------------------------
        session_row = session_block.parent
        if session_row is None:
            raise ValueError(f"Session block has no parent row: {session_block}")

        time_cell = session_row.findChild()
        if time_cell is None:
            raise ValueError(f"Could not find time cell in session row: {session_row}")

        session_start_time = int(time_cell.text.replace(":", ""))

        # -- Duration ----------------------------------------------------------
        session_duration = int(str(session_block.get("rowspan") or 1))

        # -- Teachers ----------------------------------------------------------
        matches: list[str] = re.findall(r"\[(.*?)\]", session_block.text)
        if len(matches) < 2:
            raise ValueError(
                f"Expected at least 2 bracket groups (turmas, teachers) in session block, got {len(matches)}: {session_block.text!r}",
            )

        raw_turmas, raw_teachers, *rest = matches

        session_teachers: list[int] = []
        session_teacher_acronyms = re.split(r";\s*", re.sub(r"[()]", "", raw_teachers))
        for acronym in session_teacher_acronyms:
            if acronym not in teachers_map:
                raise ValueError(
                    f"Unknown teacher acronym {acronym!r} in session block: {session_block.text!r}",
                )
            session_teachers.append(teachers_map[acronym])

        # -- Classes and Room --------------------------------------------------
        session_classes = re.split(r";\s*", raw_turmas)
        session_room = str(rest[0]).split(";") if rest else ["Online"]

        # -- Is Theoretical ----------------------------------------------------
        session_css_classes = session_block.get("class")
        if not session_css_classes:
            raise ValueError(
                f"Session block missing 'class' attribute: {session_block}",
            )

        sessions.append(
            {
                "subject_acronym": subject_acronym,
                "weekday": session_weekday,
                "start_time": session_start_time,
                "duration": session_duration,
                "teachers": session_teachers,
                "classes": session_classes,
                "rooms": session_room,
                "is_theoretical": THEORETICAL_SESSION in session_css_classes,
            },
        )

    return sessions
