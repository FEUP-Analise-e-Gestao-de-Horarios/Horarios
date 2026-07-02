"""Builders for realistic FEUP schedule HTML, used by the ingestion parser tests.

The institution's timetable pages are frame-based HTML with a handful of
``<table class="tabela_principal">`` grids. The parsers under test
(:mod:`src.ingestion.parsers`) are tightly coupled to that structure — they
index tables by position, read the 4th row of the main grid as the weekday
header, resolve session cells by CSS ``td_tipologia_*`` classes, and so on.

Rather than check in captured HTML, these helpers assemble the *minimum* markup
each parser needs, parameterised so a test can express exactly the shape it
cares about. Every builder returns an HTML ``str``; call ``soup()`` to parse.

Layout of a full class page (``class_page``), by table index:

===========  =====================  ==================================
all-tables   tabela_principal       purpose
===========  =====================  ==================================
0            tp[0]                  main schedule grid (inside <center>)
1            tp[1]                  ``Tipologias`` legend
2            —  (plain <table>)     spacer, shifts the teacher index
3            tp[2]                  teachers table
4            tp[3]                  subjects table
5            tp[4]                  filler (satisfies the >=5 tp check)
===========  =====================  ==================================

This alignment is what makes ``extract_teachers`` (reads ``tp[2]``) and
``extract_sessions`` (reads ``all[3]``) agree on the same teachers table.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from bs4 import BeautifulSoup

# The tipologia CSS class the fixtures use for a plain "T" (theoretical) block.
TIPOLOGIA_T = "td_tipologia_19"
TIPOLOGIA_TP = "td_tipologia_4"


def soup(html: str) -> BeautifulSoup:
    """Parse an HTML string the same way the scraper does."""
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# -- Cells
# ---------------------------------------------------------------------------


def empty_cell() -> str:
    return "<td></td>"


def time_cell(label: str) -> str:
    return f"<td>{label}</td>"


def red_cell() -> str:
    return '<td class="td_vermelha"></td>'


def weekday_header(days: Sequence[tuple[str, int]]) -> str:
    """Build the weekday header row (matrix row 0).

    ``days`` is a sequence of ``(portuguese_name, colspan)`` pairs. Column 0 is
    a spacer for the time-label column.
    """
    cells = ["<td></td>"]
    cells += [f'<td colspan="{span}">{name}</td>' for name, span in days]
    return "<tr>" + "".join(cells) + "</tr>"


def session_cell(
    *,
    subject_acronym: str = "PROG",
    year: int = 2024,
    number: int = 3,
    classes: Sequence[str] = ("1LEIC01",),
    teachers: Sequence[str] = ("ABC",),
    rooms: Sequence[str] | None = ("B001",),
    tipologia: str = TIPOLOGIA_T,
    rowspan: int = 1,
) -> str:
    """Build a single ``td_tipologia_*`` session block cell.

    The rendered text is ``"{acronym} ({year} - {number})[classes][teachers][rooms]"``,
    which is exactly what :func:`extract_sessions` expects. Pass ``rooms=None``
    to omit the room bracket group (an online session).
    """
    header = f"{subject_acronym} ({year} - {number})"
    parts = [header]
    parts.append(f"[{'; '.join(classes)}]")
    parts.append(f"[{'; '.join(teachers)}]")
    if rooms is not None:
        parts.append(f"[{'; '.join(rooms)}]")
    inner = "<br/>".join(parts)
    return f'<td class="{tipologia} td_sessao" rowspan="{rowspan}">{inner}</td>'


# ---------------------------------------------------------------------------
# -- Tables
# ---------------------------------------------------------------------------


def _rows(rows: Iterable[str]) -> str:
    return "".join(rows)


def main_schedule_table(
    *,
    days: Sequence[tuple[str, int]],
    time_rows: Sequence[Sequence[str]],
    header_extra: str = "",
) -> str:
    """Assemble the main ``tabela_principal`` grid.

    Emits three placeholder header rows (the parsers skip ``tr[:3]``), then the
    weekday header at row index 3, then one ``<tr>`` per entry in ``time_rows``.
    Each ``time_rows`` entry is the full list of ``<td>`` cell strings for that
    row, including the leading time-label cell.

    ``header_extra`` is raw ``<td>`` markup injected as the first header row —
    used to carry the ``cabtitulo`` date cell on class pages.
    """
    header = [
        f"<tr>{header_extra or '<td>h0</td>'}</tr>",
        "<tr><td>h1</td></tr>",
        "<tr><td>h2</td></tr>",
        weekday_header(days),
    ]
    body = [f"<tr>{_rows(cells)}</tr>" for cells in time_rows]
    return '<table class="tabela_principal">' + _rows(header) + _rows(body) + "</table>"


def tipologias_legend(mapping: Sequence[tuple[str, str]]) -> str:
    """Build the ``Tipologias`` legend table.

    ``mapping`` is a sequence of ``(type_code, tipologia_css_class)`` pairs, e.g.
    ``[("T", TIPOLOGIA_T), ("TP", TIPOLOGIA_TP)]``. The first cell of each data
    row is the type code; the third cell carries the colour CSS class.
    """
    header = '<tr><td class="td_cabecalho">Tipologias</td></tr><tr><td>col headers</td></tr>'
    rows = [
        f'<tr><td>{code}</td><td>desc</td><td class="{css}">&nbsp;</td></tr>'
        for code, css in mapping
    ]
    return '<table class="tabela_principal">' + header + _rows(rows) + "</table>"


def teachers_table(teachers: Sequence[tuple[int, str, str]]) -> str:
    """Build the teachers table (``tp[2]`` / ``all[3]``).

    ``teachers`` is a sequence of ``(code, acronym, name)`` tuples. Each data row
    renders as ``["{code} - {name}", "{acronym}", "{code}"]`` across three cells.
    """
    header = "<tr><td>Docentes</td></tr><tr><td>col headers</td></tr>"
    rows = [
        f"<tr><td>{code} - {name}</td><td>{acronym}</td><td>{code}</td></tr>"
        for code, acronym, name in teachers
    ]
    return '<table class="tabela_principal">' + header + _rows(rows) + "</table>"


def subjects_table(subjects: Sequence[tuple[str, str, str, int, int]]) -> str:
    """Build the subjects table (``all[4]``).

    ``subjects`` is a sequence of ``(code, name, acronym, year, count)`` tuples.
    Each data row renders as ``["{code} - {name}", "{acronym}({year} - {count})",
    "{count}"]``. Note the third cell (the enrolled count) becomes the subject's
    ``number`` field.
    """
    header = "<tr><td>UCs</td></tr><tr><td>col headers</td></tr>"
    rows = [
        f"<tr><td>{code} - {name}</td><td>{acronym}({year} - {number})</td><td>{count}</td></tr>"
        for code, name, acronym, year, number, count in _normalize_subjects(subjects)
    ]
    return '<table class="tabela_principal">' + header + _rows(rows) + "</table>"


def _normalize_subjects(
    subjects: Sequence[tuple[str, str, str, int, int]],
) -> list[tuple[str, str, str, int, int, int]]:
    # Accept (code, name, acronym, year, count): the acronym's parenthetical
    # "number" mirrors the count, matching how real pages render the cell.
    out: list[tuple[str, str, str, int, int, int]] = []
    for code, name, acronym, year, count in subjects:
        out.append((code, name, acronym, year, count, count))
    return out


def filler_table() -> str:
    """A benign extra ``tabela_principal`` so the >=5 count check passes."""
    return '<table class="tabela_principal"><tr><td>filler</td></tr></table>'


def spacer_table() -> str:
    """A plain (non-``tabela_principal``) table that shifts the all-tables index."""
    return "<table><tr><td>spacer</td></tr></table>"


def cabtitulo(start: str = "15/09/2025", end: str = "21/09/2025") -> str:
    """The date-range cell read by :func:`extract_week_dates`."""
    return f'<td class="cabtitulo">Turma X<br/>{start} a {end}</td>'


# ---------------------------------------------------------------------------
# -- Whole pages
# ---------------------------------------------------------------------------


def class_page(
    *,
    days: Sequence[tuple[str, int]] = (("Segunda", 1), ("Terça", 1)),
    time_rows: Sequence[Sequence[str]] | None = None,
    teachers: Sequence[tuple[int, str, str]] = ((123, "ABC", "Ada Berta Costa"),),
    subjects: Sequence[tuple[str, str, str, int, int]] = (
        ("L.EIC001", "Programação", "PROG", 2024, 120),
    ),
    tipologias: Sequence[tuple[str, str]] = ((("T", TIPOLOGIA_T)),),
    start: str = "15/09/2025",
    end: str = "21/09/2025",
    red_blocks_in_main: bool = False,
) -> str:
    """Assemble a complete class schedule page.

    Defaults produce a one-session Monday-09:00 page taught by ABC in room B001
    for subject PROG. Override ``time_rows`` for custom grids.
    """
    if time_rows is None:
        row_9 = [time_cell("09:00"), session_cell(rowspan=1), empty_cell()]
        if red_blocks_in_main:
            row_10 = [time_cell("10:00"), red_cell(), empty_cell()]
        else:
            row_10 = [time_cell("10:00"), empty_cell(), empty_cell()]
        time_rows = [row_9, row_10]

    # cabtitulo rides in the main grid's first header row, so it does not add
    # an extra table and shift the position-indexed table lookups.
    main = main_schedule_table(
        days=days,
        time_rows=time_rows,
        header_extra=cabtitulo(start, end),
    )
    center = f"<center>{main}</center>"
    body = (
        center
        + tipologias_legend(tipologias)
        + spacer_table()
        + teachers_table(teachers)
        + subjects_table(subjects)
        + filler_table()
    )
    return f"<html><body>{body}</body></html>"


def teacher_page(
    *,
    acronym: str = "ABC",
    name: str = "Ada Berta Costa",
    code: int = 123,
    first_node: str | None = None,
    days: Sequence[tuple[str, int]] = (("Segunda", 1), ("Terça", 1)),
    red_time_rows: Sequence[Sequence[str]] | None = None,
) -> str:
    """Assemble a teacher page: a ``cabtitulo`` header plus an optional red grid.

    The ``cabtitulo`` contents drive :func:`extract_teacher_info`, which reads
    three ``<br/>``-separated text nodes: ``"{acronym} - {name}"``, the bare
    ``{acronym}``, then ``{code}``. Override ``first_node`` to exercise the
    parser's alternate formatting branches.
    """
    first = first_node if first_node is not None else f"{acronym} - {name}"
    cab = f'<td class="cabtitulo">{first}<br/>{acronym}<br/>{code}</td>'
    header_table = f"<table><tr>{cab}</tr></table>"

    if red_time_rows is None:
        grid = ""
    else:
        grid = "<center>" + main_schedule_table(days=days, time_rows=red_time_rows) + "</center>"
    return f"<html><body>{header_table}{grid}</body></html>"


def room_page(
    *,
    days: Sequence[tuple[str, int]] = (("Segunda", 1), ("Terça", 1)),
    red_time_rows: Sequence[Sequence[str]] | None = None,
) -> str:
    """Assemble a room timetable page — only red blocks are parsed from it."""
    if red_time_rows is None:
        red_time_rows = [[time_cell("09:00"), red_cell(), empty_cell()]]
    grid = "<center>" + main_schedule_table(days=days, time_rows=red_time_rows) + "</center>"
    return f"<html><body>{grid}</body></html>"


# ---------------------------------------------------------------------------
# -- Menu pages
# ---------------------------------------------------------------------------


def frame_page(menu_src: str = "menu.html") -> str:
    """The root page: a frameset whose ``links`` frame points at the menu."""
    return (
        "<html><frameset>"
        '<frame name="content" src="content.html"/>'
        f'<frame name="links" src="{menu_src}"/>'
        "</frameset></html>"
    )


def _teacher_department_li(department: str, links: Sequence[tuple[str, str]]) -> str:
    """One department ``<li>``; only its first teacher link is extracted."""
    inner = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in links)
    return f"<li><a>{department}</a><ul>{inner}</ul></li>"


def _degree_li(
    acronym: str,
    name: str,
    years: Sequence[tuple[int, Sequence[tuple[str, Sequence[str]]]]],
) -> str:
    year_lis = []
    for number, classes in years:
        class_lis = []
        for code, week_links in classes:
            weeks = "".join(f'<li><a href="{h}">S{i}</a></li>' for i, h in enumerate(week_links))
            class_lis.append(f"<li><a>{code}</a><ul>{weeks}</ul></li>")
        # year > plan_ul > plan_li > class_ul > class_li
        year_lis.append(
            f"<li><a>Ano {number}</a><ul><li><ul>{''.join(class_lis)}</ul></li></ul></li>",
        )
    return f"<li><a>{acronym} - {name}</a><ul>{''.join(year_lis)}</ul></li>"


def _room_li(name: str, link: str, *, cf_email: bool = False) -> str:
    if cf_email:
        name_anchor = (
            '<a><span class="__cf_email__" data-cfemail="abc">[email protected]</span></a>'
        )
    else:
        name_anchor = f"<a>{name}</a>"
    return f'<li>{name_anchor}<a class="timetable-link" href="{link}">horário</a></li>'


def menu_page(
    *,
    teacher_departments: Sequence[tuple[str, Sequence[tuple[str, str]]]] = (
        ("DEI", (("teacher/abc.html", "Ada Berta Costa"),)),
    ),
    degrees: Sequence[
        tuple[str, str, Sequence[tuple[int, Sequence[tuple[str, Sequence[str]]]]]]
    ] = (
        (
            "LEIC",
            "Licenciatura em Engenharia Informatica",
            ((1, (("1LEIC01", ("class/w1.html",)),)),),
        ),
    ),
    rooms: Sequence[tuple[str, str, bool]] = (("B001", "room/b001.html", False),),
) -> str:
    """Assemble the navigation menu page (``<ul id="menu">``).

    Each section is optional in shape via its argument. See the individual
    ``_*_li`` helpers for the nested structure each parser walks.
    """
    teacher_lis = "".join(_teacher_department_li(dep, links) for dep, links in teacher_departments)
    teachers_section = f"<li><a>Docentes</a><ul>{teacher_lis}</ul></li>"

    degree_lis = "".join(_degree_li(ac, nm, yrs) for ac, nm, yrs in degrees)
    classes_section = f"<li><a>Turmas</a><ul>{degree_lis}</ul></li>"

    room_lis = "".join(_room_li(nm, link, cf_email=cf) for nm, link, cf in rooms)
    rooms_section = f"<li><a>Salas</a><ul>{room_lis}</ul></li>"

    return (
        "<html><body>"
        '<ul id="menu">'
        f"{teachers_section}{classes_section}{rooms_section}"
        "</ul>"
        "</body></html>"
    )
