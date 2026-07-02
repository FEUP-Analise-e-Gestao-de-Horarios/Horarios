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
