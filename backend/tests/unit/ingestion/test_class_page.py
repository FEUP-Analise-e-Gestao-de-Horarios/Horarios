"""Unit tests for :mod:`src.ingestion.parsers.class_page`.

The class page is the richest FEUP page: it carries the week date range, the
teacher and subject tables, the ``Tipologias`` legend, and the main timetable
grid of ``td_tipologia_*`` session blocks. Each parser is exercised here for
its happy path and its structural error branches.
"""

import pytest
from bs4 import BeautifulSoup

from src.ingestion.parsers.class_page import (
    extract_sessions,
    extract_subjects,
    extract_teachers,
    extract_tipologia_map,
    extract_week_dates,
)
from src.ingestion.schemas.misc import WeekDay
from tests.unit.ingestion import _html as H


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _page(**kwargs: object) -> BeautifulSoup:
    return _soup(H.class_page(**kwargs))


# ---------------------------------------------------------------------------
# -- extract_week_dates
# ---------------------------------------------------------------------------


def test_week_dates_parsed_from_cabtitulo() -> None:
    import datetime

    start, end = extract_week_dates(_page(start="15/09/2025", end="21/09/2025"))
    assert start == datetime.date(2025, 9, 15)
    assert end == datetime.date(2025, 9, 21)


def test_week_dates_missing_cabtitulo_raises() -> None:
    with pytest.raises(ValueError, match="cabtitulo"):
        extract_week_dates(_soup("<html><body>nothing</body></html>"))


def test_week_dates_without_dates_raises() -> None:
    html = '<html><body><td class="cabtitulo">Turma sem datas</td></body></html>'
    with pytest.raises(ValueError, match="Could not find dates"):
        extract_week_dates(_soup(html))


# ---------------------------------------------------------------------------
# -- extract_teachers
# ---------------------------------------------------------------------------


def test_teachers_parsed() -> None:
    page = _page(teachers=[(123, "ABC", "Ada Costa"), (456, "DEF", "Duarte Faria")])
    assert extract_teachers(page) == [
        {"code": 123, "acronym": "ABC", "name": "Ada Costa"},
        {"code": 456, "acronym": "DEF", "name": "Duarte Faria"},
    ]


def test_teachers_name_without_dash_uses_full_cell() -> None:
    """When the first cell has no ``" - "`` separator, the whole cell is the name."""
    tables = "".join(
        '<table class="tabela_principal"><tr><td>x</td></tr></table>'
        if i != 2
        else (
            '<table class="tabela_principal">'
            "<tr><td>h0</td></tr><tr><td>h1</td></tr>"
            "<tr><td>PlainName</td><td>XYZ</td><td>7</td></tr>"
            "</table>"
        )
        for i in range(5)
    )
    (teacher,) = extract_teachers(_soup(f"<html><body>{tables}</body></html>"))
    assert teacher == {"code": 7, "acronym": "XYZ", "name": "PlainName"}


def test_teachers_too_few_tables_raises() -> None:
    html = '<table class="tabela_principal"></table>' * 3
    with pytest.raises(ValueError, match="at least 5 tables"):
        extract_teachers(_soup(html))


def test_teachers_wrong_cell_count_raises() -> None:
    tables = "".join(
        '<table class="tabela_principal"><tr><td>x</td></tr></table>'
        if i != 2
        else (
            '<table class="tabela_principal">'
            "<tr><td>h0</td></tr><tr><td>h1</td></tr>"
            "<tr><td>a</td><td>b</td></tr>"  # only 2 cells
            "</table>"
        )
        for i in range(5)
    )
    with pytest.raises(ValueError, match="exactly 3 cells"):
        extract_teachers(_soup(f"<html><body>{tables}</body></html>"))


# ---------------------------------------------------------------------------
# -- extract_subjects
# ---------------------------------------------------------------------------


def test_subjects_parsed() -> None:
    page = _page(
        subjects=[
            ("L.EIC001", "Programação", "PROG", 2024, 120),
            ("L.EIC002", "Álgebra", "ALG", 2024, 90),
        ],
    )
    assert extract_subjects(page) == [
        {"code": "L.EIC001", "name": "Programação", "acronym": "PROG", "number": 120},
        {"code": "L.EIC002", "name": "Álgebra", "acronym": "ALG", "number": 90},
    ]


def test_subjects_too_few_tables_raises() -> None:
    html = "<table></table>" * 3
    with pytest.raises(ValueError, match="at least 5 tables"):
        extract_subjects(_soup(html))


def test_subjects_bad_acronym_format_raises() -> None:
    tables = "".join(
        "<table><tr><td>x</td></tr></table>"
        if i != 4
        else (
            "<table>"
            "<tr><td>h0</td></tr><tr><td>h1</td></tr>"
            "<tr><td>L.EIC1 - Prog</td><td>NOPARENS</td><td>10</td></tr>"
            "</table>"
        )
        for i in range(5)
    )
    with pytest.raises(ValueError, match="Unexpected acronym format"):
        extract_subjects(_soup(f"<html><body>{tables}</body></html>"))


def test_subjects_no_rows_raises() -> None:
    tables = "".join(
        "<table><tr><td>x</td></tr></table>"
        if i != 4
        else "<table><tr><td>h0</td></tr><tr><td>h1</td></tr></table>"
        for i in range(5)
    )
    with pytest.raises(ValueError, match="No subjects rows"):
        extract_subjects(_soup(f"<html><body>{tables}</body></html>"))


# ---------------------------------------------------------------------------
# -- extract_tipologia_map
# ---------------------------------------------------------------------------


def test_tipologia_map_parsed() -> None:
    legend = H.tipologias_legend([("T", H.TIPOLOGIA_T), ("TP", H.TIPOLOGIA_TP)])
    assert extract_tipologia_map(_soup(legend)) == {
        H.TIPOLOGIA_T: "T",
        H.TIPOLOGIA_TP: "TP",
    }


def test_tipologia_map_missing_legend_raises() -> None:
    html = '<table class="tabela_principal"><tr><td>other</td></tr></table>'
    with pytest.raises(ValueError, match="Tipologias"):
        extract_tipologia_map(_soup(html))


def test_tipologia_map_no_data_rows_raises() -> None:
    with pytest.raises(ValueError, match="no data rows"):
        extract_tipologia_map(_soup(H.tipologias_legend([])))


def test_tipologia_map_conflicting_mapping_raises() -> None:
    legend = H.tipologias_legend([("T", H.TIPOLOGIA_T), ("TP", H.TIPOLOGIA_T)])
    with pytest.raises(ValueError, match="Conflicting tipologia"):
        extract_tipologia_map(_soup(legend))


def test_tipologia_map_empty_code_raises() -> None:
    legend = H.tipologias_legend([("", H.TIPOLOGIA_T)])
    with pytest.raises(ValueError, match="Empty type code"):
        extract_tipologia_map(_soup(legend))


# ---------------------------------------------------------------------------
# -- extract_sessions
# ---------------------------------------------------------------------------


def test_sessions_single_default() -> None:
    (session,) = extract_sessions(_page())
    assert session == {
        "subject_acronym": "PROG",
        "weekday": WeekDay.MONDAY,
        "start_time": 900,
        "duration": 1,
        "teachers": [123],
        "classes": ["1LEIC01"],
        "rooms": ["B001"],
        "type": "T",
    }


def test_sessions_none_returns_empty() -> None:
    page = _page(time_rows=[[H.time_cell("09:00"), H.empty_cell(), H.empty_cell()]])
    assert extract_sessions(page) == []


def test_sessions_online_has_online_room() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), H.session_cell(rooms=None), H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    assert extract_sessions(page)[0]["rooms"] == ["Online"]


def test_sessions_rowspan_is_duration_and_column_is_weekday() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("11:00"), H.empty_cell(), H.session_cell(rowspan=3)],
            [H.time_cell("12:00"), H.empty_cell()],
            [H.time_cell("13:00"), H.empty_cell()],
        ],
    )
    (session,) = extract_sessions(page)
    assert session["duration"] == 3
    assert session["start_time"] == 1100
    assert session["weekday"] == WeekDay.TUESDAY


def test_sessions_multiple_teachers_and_classes_and_tp_type() -> None:
    page = _page(
        time_rows=[
            [
                H.time_cell("09:00"),
                H.session_cell(
                    subject_acronym="ALG",
                    classes=("1LEIC01", "1LEIC02"),
                    teachers=("ABC", "DEF"),
                    tipologia=H.TIPOLOGIA_TP,
                ),
                H.empty_cell(),
            ],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
        teachers=[(123, "ABC", "Ada"), (456, "DEF", "Duarte")],
        subjects=[("L.EIC002", "Álgebra", "ALG", 2024, 90)],
        tipologias=[("T", H.TIPOLOGIA_T), ("TP", H.TIPOLOGIA_TP)],
    )
    (session,) = extract_sessions(page)
    assert session["teachers"] == [123, 456]
    assert session["classes"] == ["1LEIC01", "1LEIC02"]
    assert session["type"] == "TP"


def test_sessions_unknown_teacher_acronym_raises() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), H.session_cell(teachers=("ZZZ",)), H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    with pytest.raises(ValueError, match="Unknown teacher acronym"):
        extract_sessions(page)


def test_sessions_unknown_tipologia_class_raises() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), H.session_cell(tipologia="td_tipologia_99"), H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    with pytest.raises(ValueError, match="Unknown tipologia class"):
        extract_sessions(page)


def test_sessions_bad_subject_acronym_raises() -> None:
    bad_cell = (
        '<td class="td_tipologia_19 td_sessao">NOPARENS<br/>[1LEIC01]<br/>[ABC]<br/>[B001]</td>'
    )
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), bad_cell, H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    with pytest.raises(ValueError, match="Unexpected acronym format"):
        extract_sessions(page)


def test_sessions_too_few_bracket_groups_raises() -> None:
    bad_cell = '<td class="td_tipologia_19 td_sessao">PROG (2024 - 3)<br/>[1LEIC01]</td>'
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), bad_cell, H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    with pytest.raises(ValueError, match="at least 2 bracket groups"):
        extract_sessions(page)


def test_sessions_missing_center_raises() -> None:
    with pytest.raises(ValueError, match="center"):
        extract_sessions(_soup('<html><body><td class="td_tipologia_19">x</td></body></html>'))


# ---------------------------------------------------------------------------
# -- Local helpers for malformed / hand-built markup
# ---------------------------------------------------------------------------


def _default_time_rows() -> list[list[str]]:
    """One PROG session at Monday 09:00 plus an empty 10:00 row."""
    return [
        [H.time_cell("09:00"), H.session_cell(rowspan=1), H.empty_cell()],
        [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
    ]


def _assemble_page(
    *,
    teachers_table_html: str,
    time_rows: list[list[str]] | None = None,
    tipologias: tuple[tuple[str, str], ...] = (("T", H.TIPOLOGIA_T),),
) -> BeautifulSoup:
    """Assemble a class page identical to ``H.class_page`` but with a custom teachers table.

    Mirrors the table layout of :func:`_html.class_page` exactly (main grid in a
    ``<center>``, then the Tipologias legend, a spacer, the teachers table, the
    subjects table, and the filler) so ``all_tables[3]`` is the teachers table.
    """
    if time_rows is None:
        time_rows = _default_time_rows()
    main = H.main_schedule_table(
        days=(("Segunda", 1), ("Terça", 1)),
        time_rows=time_rows,
        header_extra=H.cabtitulo(),
    )
    body = (
        f"<center>{main}</center>"
        + H.tipologias_legend(tipologias)
        + H.spacer_table()
        + teachers_table_html
        + H.subjects_table((("L.EIC001", "Programação", "PROG", 2024, 120),))
        + H.filler_table()
    )
    return _soup(f"<html><body>{body}</body></html>")


def _cabtitulo_soup(text: str) -> BeautifulSoup:
    """A minimal page whose ``cabtitulo`` last text node is ``text``."""
    return _soup(f'<html><body><td class="cabtitulo">Turma X<br/>{text}</td></body></html>')


def _five_tables(index: int, table_html: str) -> BeautifulSoup:
    """Five plain tables where ``all_tables[index]`` is ``table_html``."""
    tables = "".join(
        table_html if i == index else "<table><tr><td>x</td></tr></table>" for i in range(5)
    )
    return _soup(f"<html><body>{tables}</body></html>")


# ---------------------------------------------------------------------------
# -- Gap 1: extract_sessions duplicate teacher acronym (line 307)
# ---------------------------------------------------------------------------


def test_sessions_duplicate_teacher_acronym_raises() -> None:
    """extract_sessions builds its own teachers_map and rejects duplicate acronyms."""
    page = _page(teachers=[(123, "ABC", "A"), (456, "ABC", "B")])
    with pytest.raises(ValueError, match="Duplicate teacher acronym"):
        extract_sessions(page)


def test_teachers_duplicate_acronym_is_accepted() -> None:
    """Asymmetry companion: extract_teachers does NOT dedup acronyms, unlike extract_sessions."""
    page = _page(teachers=[(123, "ABC", "A"), (456, "ABC", "B")])
    assert extract_teachers(page) == [
        {"code": 123, "acronym": "ABC", "name": "A"},
        {"code": 456, "acronym": "ABC", "name": "B"},
    ]


# ---------------------------------------------------------------------------
# -- Gap 2: extract_sessions teachers-table shape errors (lines 295, 301)
# ---------------------------------------------------------------------------


def test_sessions_teacher_row_wrong_cell_count_raises() -> None:
    bad_teachers = (
        '<table class="tabela_principal">'
        "<tr><td>Docentes</td></tr><tr><td>col headers</td></tr>"
        "<tr><td>a</td><td>b</td></tr>"  # only 2 cells
        "</table>"
    )
    with pytest.raises(ValueError, match="exactly 3 cells"):
        extract_sessions(_assemble_page(teachers_table_html=bad_teachers))


def test_sessions_no_teacher_rows_raises() -> None:
    no_rows = (
        '<table class="tabela_principal">'
        "<tr><td>Docentes</td></tr><tr><td>col headers</td></tr>"  # header rows only
        "</table>"
    )
    with pytest.raises(ValueError, match="No teacher rows found"):
        extract_sessions(_assemble_page(teachers_table_html=no_rows))


# ---------------------------------------------------------------------------
# -- Gap 3: extract_sessions <4-tables guard (line 290)
# ---------------------------------------------------------------------------


def test_sessions_too_few_tables_raises() -> None:
    """Only the main grid + legend are present (2 tables), tripping the >=4 guard."""
    main = H.main_schedule_table(
        days=(("Segunda", 1), ("Terça", 1)),
        time_rows=_default_time_rows(),
        header_extra=H.cabtitulo(),
    )
    body = f"<center>{main}</center>" + H.tipologias_legend((("T", H.TIPOLOGIA_T),))
    with pytest.raises(ValueError, match="at least 4 tables"):
        extract_sessions(_soup(f"<html><body>{body}</body></html>"))


# ---------------------------------------------------------------------------
# -- Gap 4 / 9: extract_tipologia_map colour-class + cell-count branches (202, 216)
# ---------------------------------------------------------------------------


def _legend(rows: str) -> BeautifulSoup:
    header = '<tr><td class="td_cabecalho">Tipologias</td></tr><tr><td>col headers</td></tr>'
    return _soup(f'<table class="tabela_principal">{header}{rows}</table>')


def test_tipologia_map_missing_colour_class_raises() -> None:
    rows = '<tr><td>T</td><td>desc</td><td class="other">&nbsp;</td></tr>'
    with pytest.raises(ValueError, match=r"No 'td_tipologia_\*' class"):
        extract_tipologia_map(_legend(rows))


def test_tipologia_map_wrong_cell_count_raises() -> None:
    rows = "<tr><td>T</td><td>desc</td></tr>"  # only 2 cells
    with pytest.raises(ValueError, match="exactly 3 cells in tipologias"):
        extract_tipologia_map(_legend(rows))


def test_tipologia_map_third_cell_no_class_attr_raises() -> None:
    """Gap 9 companion: a 3-cell row whose colour cell carries no class at all."""
    rows = "<tr><td>T</td><td>desc</td><td>&nbsp;</td></tr>"
    with pytest.raises(ValueError, match=r"No 'td_tipologia_\*' class"):
        extract_tipologia_map(_legend(rows))


def test_tipologia_map_non_tipologia_class_raises() -> None:
    """Gap 9 companion: colour cell has a class, but not a ``td_tipologia_*`` one."""
    rows = '<tr><td>T</td><td>desc</td><td class="not_a_tipologia">&nbsp;</td></tr>'
    with pytest.raises(ValueError, match=r"No 'td_tipologia_\*' class"):
        extract_tipologia_map(_legend(rows))


# ---------------------------------------------------------------------------
# -- Gap 5: extract_subjects wrong-cell-count branch (line 139)
# ---------------------------------------------------------------------------


def test_subjects_wrong_cell_count_raises() -> None:
    table = (
        "<table><tr><td>h0</td></tr><tr><td>h1</td></tr>"
        "<tr><td>a</td><td>b</td></tr>"  # only 2 cells
        "</table>"
    )
    with pytest.raises(ValueError, match="exactly 3 cells in row"):
        extract_subjects(_five_tables(4, table))


# ---------------------------------------------------------------------------
# -- Gap 6 (SOURCE FIX): extract_subjects code cell without ' - ' separator
# ---------------------------------------------------------------------------


def test_subjects_code_cell_without_dash_raises() -> None:
    """A subjects code cell lacking ``" - "`` must raise a descriptive ValueError."""
    table = (
        "<table><tr><td>h0</td></tr><tr><td>h1</td></tr>"
        "<tr><td>NODASH</td><td>PROG(2024 - 3)</td><td>10</td></tr>"
        "</table>"
    )
    with pytest.raises(ValueError, match="Expected '<code> - <name>' format in subject cell"):
        extract_subjects(_five_tables(4, table))


# ---------------------------------------------------------------------------
# -- Gap 7: extract_sessions main-table shape guards (lines 269, 276)
# ---------------------------------------------------------------------------


def test_sessions_main_table_not_tabela_principal_raises() -> None:
    """Session blocks live in <center> but not inside a ``tabela_principal`` grid."""
    plain = (
        "<table><tr><td>09:00</td>"
        '<td class="td_tipologia_19 td_sessao">PROG (2024 - 3)<br/>[1LEIC01]<br/>[ABC]</td>'
        "</tr></table>"
    )
    body = (
        f"<center>{plain}</center>"
        + H.tipologias_legend((("T", H.TIPOLOGIA_T),))
        + H.spacer_table()
        + H.teachers_table(((123, "ABC", "A"),))
        + H.subjects_table((("L.EIC001", "P", "PROG", 2024, 1),))
        + H.filler_table()
    )
    with pytest.raises(ValueError, match="Could not find 'tabela_principal'"):
        extract_sessions(_soup(f"<html><body>{body}</body></html>"))


def test_sessions_main_table_too_few_rows_raises() -> None:
    """A ``tabela_principal`` main grid whose direct <tr> children number < 4."""
    # The weekday header + session row are nested one level deep so the matrix
    # (which reads all descendant <tr>) is well-formed, but the main table's
    # direct-child <tr> count is 3, tripping the "at least 4 rows" guard.
    inner = (
        H.weekday_header((("Segunda", 1), ("Terça", 1)))
        + f"<tr><td>09:00</td>{H.session_cell()}<td></td></tr>"
    )
    main = (
        '<table class="tabela_principal">'
        "<tr><td>h0</td></tr><tr><td>h1</td></tr>"
        f"<tr><td><table>{inner}</table></td></tr>"
        "</table>"
    )
    body = (
        f"<center>{main}</center>"
        + H.tipologias_legend((("T", H.TIPOLOGIA_T),))
        + H.spacer_table()
        + H.teachers_table(((123, "ABC", "A"),))
        + H.subjects_table((("L.EIC001", "P", "PROG", 2024, 1),))
        + H.filler_table()
    )
    with pytest.raises(ValueError, match="at least 4 rows in 'tabela_principal'"):
        extract_sessions(_soup(f"<html><body>{body}</body></html>"))


# ---------------------------------------------------------------------------
# -- Gap 8: multi-room parsing + red-cell exclusion (lines 366-367)
# ---------------------------------------------------------------------------


def test_sessions_multiple_rooms_and_red_cell_excluded() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), H.session_cell(rooms=("B001", "B002")), H.empty_cell()],
            [H.time_cell("10:00"), H.red_cell(), H.empty_cell()],
        ],
    )
    sessions = extract_sessions(page)
    # The red (``td_vermelha``) cell must NOT be parsed as a session.
    assert len(sessions) == 1
    assert sessions[0]["rooms"] == ["B001", "B002"]


# ---------------------------------------------------------------------------
# -- Gap 10: teacher-table + empty-acronym error branches (294-295, 306-307, 326-327)
# ---------------------------------------------------------------------------


def test_sessions_no_teacher_rows_branch() -> None:
    no_rows = (
        '<table class="tabela_principal">'
        "<tr><td>Docentes</td></tr><tr><td>col headers</td></tr>"
        "</table>"
    )
    with pytest.raises(ValueError, match="No teacher rows found"):
        extract_sessions(_assemble_page(teachers_table_html=no_rows))


def test_sessions_duplicate_teacher_branch() -> None:
    page = _page(teachers=[(1, "ABC", "A"), (2, "ABC", "B")])
    with pytest.raises(ValueError, match="Duplicate teacher acronym"):
        extract_sessions(page)


def test_sessions_whitespace_subject_acronym_raises() -> None:
    """A whitespace-only subject header.

    The source strips the raw header before matching, so a purely whitespace
    acronym collapses to ``"(2024 - 3)"`` which fails the acronym regex and
    raises "Unexpected acronym format" (the ``Empty subject acronym`` guard at
    lines 326-327 is unreachable because of that leading strip).
    """
    cell = (
        '<td class="td_tipologia_19 td_sessao"> (2024 - 3)<br/>[1LEIC01]<br/>[ABC]<br/>[B001]</td>'
    )
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), cell, H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    with pytest.raises(ValueError, match="Unexpected acronym format"):
        extract_sessions(page)


# ---------------------------------------------------------------------------
# -- Gap 11: numeric/format cell false-positives (lines 103, 144, 145)
# ---------------------------------------------------------------------------


def test_subjects_non_numeric_count_raises() -> None:
    table = (
        "<table><tr><td>h0</td></tr><tr><td>h1</td></tr>"
        "<tr><td>L.EIC1 - Prog</td><td>PROG(2024 - 3)</td><td>N/A</td></tr>"
        "</table>"
    )
    with pytest.raises(ValueError, match="invalid literal for int"):
        extract_subjects(_five_tables(4, table))


def test_subjects_code_without_dash_is_clean_reject() -> None:
    """Gap 11(b): subjects has no dash fallback (unlike teachers); it rejects cleanly."""
    table = (
        "<table><tr><td>h0</td></tr><tr><td>h1</td></tr>"
        "<tr><td>L.EIC001 Prog</td><td>PROG(2024 - 3)</td><td>10</td></tr>"
        "</table>"
    )
    with pytest.raises(ValueError, match="Expected '<code> - <name>' format in subject cell"):
        extract_subjects(_five_tables(4, table))


def test_teachers_non_numeric_code_raises() -> None:
    tables = "".join(
        '<table class="tabela_principal"><tr><td>x</td></tr></table>'
        if i != 2
        else (
            '<table class="tabela_principal">'
            "<tr><td>h0</td></tr><tr><td>h1</td></tr>"
            "<tr><td>7 - Name</td><td>XYZ</td><td>x</td></tr>"  # non-numeric code
            "</table>"
        )
        for i in range(5)
    )
    with pytest.raises(ValueError, match="invalid literal for int"):
        extract_teachers(_soup(f"<html><body>{tables}</body></html>"))


# ---------------------------------------------------------------------------
# -- Gap 12: extract_week_dates value-domain (lines 54, 58-59)
# ---------------------------------------------------------------------------


def test_week_dates_invalid_calendar_date_raises() -> None:
    with pytest.raises(ValueError, match="does not match format"):
        extract_week_dates(_cabtitulo_soup("32/13/2025 a 21/09/2025"))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # single date: start == end (currently unasserted plausible-but-wrong shape)
        ("15/09/2025", ((2025, 9, 15), (2025, 9, 15))),
        # two dates: the ordinary happy path
        ("15/09/2025 a 21/09/2025", ((2025, 9, 15), (2025, 9, 21))),
        # three dates: takes first and last, never the middle
        ("01/09/2025 a 08/09/2025 a 15/09/2025", ((2025, 9, 1), (2025, 9, 15))),
        # four dates: first and last again
        (
            "01/01/2024 a 02/02/2024 a 03/03/2024 a 04/04/2024",
            ((2024, 1, 1), (2024, 4, 4)),
        ),
    ],
)
def test_week_dates_first_and_last(
    text: str,
    expected: tuple[tuple[int, int, int], tuple[int, int, int]],
) -> None:
    import datetime

    (sy, sm, sd), (ey, em, ed) = expected
    start, end = extract_week_dates(_cabtitulo_soup(text))
    assert start == datetime.date(sy, sm, sd)
    assert end == datetime.date(ey, em, ed)


# ---------------------------------------------------------------------------
# -- Gap 13: session cell with multiple semicolon-separated rooms (line 367)
# ---------------------------------------------------------------------------


def test_sessions_multiple_rooms_split_on_semicolon() -> None:
    page = _page(
        time_rows=[
            [H.time_cell("09:00"), H.session_cell(rooms=("B001", "B002")), H.empty_cell()],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
    )
    (session,) = extract_sessions(page)
    assert session["rooms"] == ["B001", "B002"]


# ---------------------------------------------------------------------------
# -- Gap 14: multiple sessions on one page (document order + no spurious block)
# ---------------------------------------------------------------------------


def test_sessions_multiple_blocks_ordered_by_column() -> None:
    """Two session blocks on the same page parse in document order.

    A PROG (T) block on Monday and an ALG (TP) block on Tuesday must both be
    emitted, in document order, each mapped to its own weekday/type — no block
    is dropped, duplicated, or misattributed.
    """
    page = _page(
        time_rows=[
            [
                H.time_cell("09:00"),
                H.session_cell(subject_acronym="PROG", tipologia=H.TIPOLOGIA_T),
                H.session_cell(subject_acronym="ALG", tipologia=H.TIPOLOGIA_TP),
            ],
            [H.time_cell("10:00"), H.empty_cell(), H.empty_cell()],
        ],
        subjects=[
            ("L.EIC001", "Programação", "PROG", 2024, 120),
            ("L.EIC002", "Álgebra", "ALG", 2024, 90),
        ],
        tipologias=[("T", H.TIPOLOGIA_T), ("TP", H.TIPOLOGIA_TP)],
    )
    sessions = extract_sessions(page)
    assert len(sessions) == 2
    assert [s["subject_acronym"] for s in sessions] == ["PROG", "ALG"]
    assert [s["weekday"] for s in sessions] == [WeekDay.MONDAY, WeekDay.TUESDAY]
    assert [s["type"] for s in sessions] == ["T", "TP"]


# ---------------------------------------------------------------------------
# -- Gap 15: colspan>1 weekday header mapping end-to-end through extract_sessions
# ---------------------------------------------------------------------------


def test_sessions_weekday_resolved_across_wide_colspan() -> None:
    """A session in a weekday whose header spans multiple columns resolves correctly.

    Segunda and Terça each span 2 columns (cols 1-2 and 3-4). A session block at
    column 3 must map to Terça, exercising the wide-span accumulation in
    ``get_weekday_at_column`` through the real parser, not just in isolation.
    """
    page = _page(
        days=(("Segunda", 2), ("Terça", 2)),
        time_rows=[
            [
                H.time_cell("09:00"),
                H.empty_cell(),
                H.empty_cell(),
                H.session_cell(),
                H.empty_cell(),
            ],
            [
                H.time_cell("10:00"),
                H.empty_cell(),
                H.empty_cell(),
                H.empty_cell(),
                H.empty_cell(),
            ],
        ],
    )
    (session,) = extract_sessions(page)
    assert session["weekday"] == WeekDay.TUESDAY


# ---------------------------------------------------------------------------
# -- Gap 16: tipologia legend with an identical duplicate row is allowed
# ---------------------------------------------------------------------------


def test_tipologia_map_identical_duplicate_is_allowed() -> None:
    """A repeated (code, class) pair collapses without raising (benign equal branch).

    Only a *conflicting* duplicate (same class, different code) is an error; an
    identical repeat deduplicates to a single mapping entry.
    """
    legend = H.tipologias_legend([("T", H.TIPOLOGIA_T), ("T", H.TIPOLOGIA_T)])
    assert extract_tipologia_map(_soup(legend)) == {H.TIPOLOGIA_T: "T"}
