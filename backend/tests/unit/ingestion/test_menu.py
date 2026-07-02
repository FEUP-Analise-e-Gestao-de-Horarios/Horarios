"""Unit tests for :mod:`src.ingestion.parsers.menu`.

Covers the five menu parsers that turn the navigation frame into teacher links,
the degree/year/class hierarchy, and room metadata:

* ``extract_menu_link`` — the ``<frame name="links">`` src.
* ``extract_menu_tags`` — the Docentes / Turmas / Salas ``<li>`` sections.
* ``extract_teacher_links`` — one link per department ``<li>``.
* ``extract_sessions_info`` — the nested Degree → Year → Class → weeks tree.
* ``extract_rooms_info`` — room name/metadata/timetable-link, incl. the
  Cloudflare-obfuscated ``EaD`` special case and unknown-room defaults.
"""

import pytest
from bs4 import BeautifulSoup

from src.ingestion.parsers.menu import (
    extract_menu_link,
    extract_menu_tags,
    extract_rooms_info,
    extract_sessions_info,
    extract_teacher_links,
)
from tests.unit.ingestion import _html as H


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _sections(**menu_kwargs: object):
    """Return the (teachers, classes, rooms) ``<li>`` tags for a built menu."""
    return extract_menu_tags(_soup(H.menu_page(**menu_kwargs)))


# ---------------------------------------------------------------------------
# -- extract_menu_link
# ---------------------------------------------------------------------------


def test_menu_link_returns_frame_src() -> None:
    assert extract_menu_link(_soup(H.frame_page("nav/menu.html"))) == "nav/menu.html"


def test_menu_link_missing_frame_raises() -> None:
    with pytest.raises(ValueError, match="frame with name 'links'"):
        extract_menu_link(_soup("<html><frameset></frameset></html>"))


# ---------------------------------------------------------------------------
# -- extract_menu_tags
# ---------------------------------------------------------------------------


def test_menu_tags_returns_three_sections() -> None:
    teachers, classes, rooms = _sections()
    assert teachers.find("a").get_text(strip=True) == "Docentes"
    assert classes.find("a").get_text(strip=True) == "Turmas"
    assert rooms.find("a").get_text(strip=True) == "Salas"


def test_menu_tags_missing_menu_ul_raises() -> None:
    with pytest.raises(ValueError, match="ul with id 'menu'"):
        extract_menu_tags(_soup("<html><body><p>no menu</p></body></html>"))


def test_menu_tags_missing_section_raises() -> None:
    html = (
        '<html><body><ul id="menu">'
        "<li><a>Docentes</a></li><li><a>Turmas</a></li>"
        "</ul></body></html>"
    )
    with pytest.raises(ValueError, match="Salas"):
        extract_menu_tags(_soup(html))


# ---------------------------------------------------------------------------
# -- extract_teacher_links
# ---------------------------------------------------------------------------


def test_teacher_links_single_department() -> None:
    teachers, _, _ = _sections()
    assert extract_teacher_links(teachers) == ["teacher/abc.html"]


def test_teacher_links_one_per_department() -> None:
    """Each department contributes only its first teacher anchor."""
    teachers, _, _ = _sections(
        teacher_departments=[
            ("DEI", [("t/a.html", "A"), ("t/a2.html", "A2")]),
            ("DEM", [("t/b.html", "B")]),
        ],
    )
    assert extract_teacher_links(teachers) == ["t/a.html", "t/b.html"]


def test_teacher_links_missing_inner_ul_raises() -> None:
    li = _soup("<li><a>Docentes</a><ul><li>no inner ul</li></ul></li>").find("li")
    with pytest.raises(ValueError, match="child menu item"):
        extract_teacher_links(li)


def test_teacher_links_missing_outer_ul_raises() -> None:
    li = _soup("<li><a>Docentes</a></li>").find("li")
    with pytest.raises(ValueError, match="docentes menu"):
        extract_teacher_links(li)


def test_teacher_links_missing_inner_li_raises() -> None:
    li = _soup("<li><a>Docentes</a><ul><li><ul></ul></li></ul></li>").find("li")
    with pytest.raises(ValueError, match="<li> in child menu item"):
        extract_teacher_links(li)


def test_teacher_links_missing_anchor_raises() -> None:
    li = _soup("<li><a>Docentes</a><ul><li><ul><li></li></ul></li></ul></li>").find("li")
    with pytest.raises(ValueError, match="<a> in <li>"):
        extract_teacher_links(li)


# ---------------------------------------------------------------------------
# -- extract_sessions_info
# ---------------------------------------------------------------------------


def test_sessions_info_single_degree() -> None:
    _, classes, _ = _sections()
    degrees = extract_sessions_info(classes)

    assert degrees == [
        {
            "acronym": "LEIC",
            "name": "Licenciatura em Engenharia Informatica",
            "years": [
                {
                    "number": 1,
                    "classes": [
                        {"code": "1LEIC01", "links": ["class/w1.html"], "pages": []},
                    ],
                },
            ],
        },
    ]


def test_sessions_info_multi_degree_year_class_weeks() -> None:
    _, classes, _ = _sections(
        degrees=[
            (
                "LEIC",
                "Licenciatura",
                [
                    (1, [("1LEIC01", ["w1a.html", "w1b.html"]), ("1LEIC02", ["w2.html"])]),
                    (2, [("2LEIC01", ["w3.html"])]),
                ],
            ),
            ("MEIC", "Mestrado", [(1, [("1MEIC01", ["m1.html"])])]),
        ],
    )
    degrees = extract_sessions_info(classes)

    assert [d["acronym"] for d in degrees] == ["LEIC", "MEIC"]
    leic = degrees[0]
    assert [y["number"] for y in leic["years"]] == [1, 2]
    year1 = leic["years"][0]
    assert [c["code"] for c in year1["classes"]] == ["1LEIC01", "1LEIC02"]
    assert year1["classes"][0]["links"] == ["w1a.html", "w1b.html"]


def test_sessions_info_missing_ul_raises() -> None:
    li = _soup("<li><a>Turmas</a></li>").find("li")
    with pytest.raises(ValueError, match="turmas menu"):
        extract_sessions_info(li)


def test_sessions_info_degree_without_anchor_raises() -> None:
    li = _soup("<li><a>Turmas</a><ul><li></li></ul></li>").find("li")
    with pytest.raises(ValueError, match="turmas menu child"):
        extract_sessions_info(li)


def test_sessions_info_missing_degree_children_ul_raises() -> None:
    li = _soup("<li><a>Turmas</a><ul><li><a>LEIC - Curso</a></li></ul></li>").find("li")
    with pytest.raises(ValueError, match="Could not find <ul> for curso"):
        extract_sessions_info(li)


def test_sessions_info_missing_class_ul_raises() -> None:
    # Degree -> year present, but the plano <li> has no turmas <ul>.
    html = (
        "<li><a>Turmas</a><ul>"
        "<li><a>LEIC - Curso</a><ul>"
        "<li><a>Ano 1</a><ul><li>no class ul</li></ul></li>"
        "</ul></li>"
        "</ul></li>"
    )
    with pytest.raises(ValueError, match="turmas <ul>"):
        extract_sessions_info(_soup(html).find("li"))


# ---------------------------------------------------------------------------
# -- extract_rooms_info
# ---------------------------------------------------------------------------


def test_rooms_info_known_room_metadata() -> None:
    """A room present in the ``ROOMS`` registry gets its static metadata."""
    _, _, rooms = _sections()
    assert extract_rooms_info(rooms) == [
        {
            "name": "B001",
            "type_": "Anf",
            "size": "Queijo",
            "seats": "N/A",
            "link": "room/b001.html",
        },
    ]


def test_rooms_info_unknown_room_defaults_to_desconhecido() -> None:
    _, _, rooms = _sections(rooms=[("Z999", "room/z999.html", False)])
    (room,) = extract_rooms_info(rooms)
    assert room["type_"] == "Desconhecido"
    assert room["size"] == "Desconhecido"
    assert room["seats"] == "Desconhecido"


def test_rooms_info_cloudflare_email_becomes_ead() -> None:
    _, _, rooms = _sections(rooms=[("whatever", "room/ead.html", True)])
    (room,) = extract_rooms_info(rooms)
    assert room["name"] == "EaD"
    assert room["link"] == "room/ead.html"


def test_rooms_info_no_ul_returns_empty() -> None:
    li = _soup("<li><a>Salas</a></li>").find("li")
    assert extract_rooms_info(li) == []


def test_rooms_info_missing_timetable_link_raises() -> None:
    li = _soup("<li><a>Salas</a><ul><li><a>B001</a></li></ul></li>").find("li")
    with pytest.raises(ValueError, match="timetable link"):
        extract_rooms_info(li)


def test_rooms_info_entry_without_anchor_is_skipped() -> None:
    li = _soup(
        "<li><a>Salas</a><ul>"
        "<li>no anchor here</li>"
        '<li><a>B002</a><a class="timetable-link" href="b002.html">h</a></li>'
        "</ul></li>",
    ).find("li")
    rooms = extract_rooms_info(li)
    assert [r["name"] for r in rooms] == ["B002"]
