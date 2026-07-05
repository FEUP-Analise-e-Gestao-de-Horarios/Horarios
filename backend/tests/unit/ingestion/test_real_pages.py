"""Characterization tests against **real** captured FEUP pages.

Every other ingestion test feeds the parsers synthetic HTML built by
:mod:`_html`, which encodes the same structural assumptions as the parsers
themselves — so those tests prove self-consistency, not fidelity to what
SIGARRA actually serves. The tests here run the parsers over byte-for-byte real
pages (loaded via :mod:`_fixtures`) and pin their *full* output. They do two
jobs: validate the parsers against reality once, and act as a regression
tripwire — if a parser refactor or a re-captured page changes any parsed value,
the exact diff shows up here.

Because they assert concrete real-world data, these expectations are tied to the
captured week (see :mod:`_fixtures` provenance) and are expected to change if the
fixtures are refreshed.
"""

from collections import Counter
from datetime import date, timedelta
from itertools import pairwise

import pytest

from src.ingestion.manager import IngestionManager
from src.ingestion.parsers.class_page import (
    extract_sessions,
    extract_subjects,
    extract_teachers,
    extract_tipologia_map,
    extract_week_dates,
)
from src.ingestion.parsers.menu import (
    extract_menu_link,
    extract_menu_tags,
    extract_rooms_info,
    extract_sessions_info,
    extract_teacher_links,
)
from src.ingestion.parsers.red_blocks import extract_red_blocks
from src.ingestion.parsers.teacher_page import extract_teacher_info
from src.ingestion.schemas.misc import WeekDay
from src.ingestion.scraper import Scraper
from tests.unit.ingestion import _fixtures as F
from tests.unit.ingestion._fakes import FakeSession

# ---------------------------------------------------------------------------
# -- frameset (index.html) -> extract_menu_link
# ---------------------------------------------------------------------------


def test_real_frameset_menu_link() -> None:
    """The real frameset uses upper-case ``NAME`` and a ``%3F``-encoded src."""
    assert extract_menu_link(F.soup("frameset")) == "coluna1.html%3F639044378190378436.html"


# ---------------------------------------------------------------------------
# -- menu (coluna1.html) -> the five menu parsers
# ---------------------------------------------------------------------------


def test_real_menu_sections_and_counts() -> None:
    teachers_li, classes_li, rooms_li = extract_menu_tags(F.soup("menu"))

    teacher_links = extract_teacher_links(teachers_li)
    degrees = extract_sessions_info(classes_li)
    rooms = extract_rooms_info(rooms_li)

    assert len(teacher_links) == 661
    assert (
        teacher_links[0] == "docente_AA_211315_1376_2026021620260601.html%3F639044378190378436.html"
    )

    assert len(degrees) == 51
    assert degrees[0]["acronym"] == "CINF"
    assert degrees[0]["name"] == "Licenciatura em Ciência da Informação"
    assert len(degrees[0]["years"]) == 3

    first_year = degrees[0]["years"][0]
    assert first_year["number"] == 1
    assert len(first_year["classes"]) == 3
    first_class = first_year["classes"][0]
    assert first_class["code"] == "1CINF01"
    assert (
        first_class["links"][0]
        == "turma_1CINF01_1295_2026021620260525.html%3F639044378190378436.html"
    )

    assert len(rooms) == 149


def test_real_menu_room_registry_lookup_known_and_unknown() -> None:
    """A room in the ``ROOMS`` registry gets its metadata; one absent from it
    falls back to ``Desconhecido`` for every field — both exercised by real data."""
    _, _, rooms_li = extract_menu_tags(F.soup("menu"))
    rooms = extract_rooms_info(rooms_li)

    # B001 is in the registry (Anfiteatro, "Queijo").
    assert rooms[0] == {
        "name": "B001",
        "type_": "Anf",
        "size": "Queijo",
        "seats": "N/A",
        "link": "sala_B001_813_2026021620260406.html%3F639044378190378436.html",
    }
    # R001 is NOT in the registry -> all-"Desconhecido" fallback.
    assert rooms[-1] == {
        "name": "R001",
        "type_": "Desconhecido",
        "size": "Desconhecido",
        "seats": "Desconhecido",
        "link": "sala_R001_982_2026022320260316.html%3F639044378190378436.html",
    }


# ---------------------------------------------------------------------------
# -- teacher pages (docente_*) -> extract_teacher_info + extract_red_blocks
# ---------------------------------------------------------------------------


def test_real_teacher_normal_parses_accented_name() -> None:
    """Happy path: real ``<br>`` markup, extra ``cabtitulo`` attributes and a
    trailing ``Semanas: …`` node — the accented name still parses correctly."""
    assert extract_teacher_info(F.soup("teacher_normal")) == (
        "JCR",
        "José Pedro Coelho Rodrigues",
        415643,
    )


def test_real_teacher_normal_red_blocks() -> None:
    red_blocks = extract_red_blocks(F.soup("teacher_normal"))
    assert len(red_blocks) == 27
    assert red_blocks[0] == (800, WeekDay.MONDAY)


def test_real_teacher_name_recovered_when_sigla_differs_from_acronym() -> None:
    """The header sigla is not always the acronym; the name is recovered from it.

    On this real page the ``cabtitulo`` first node is
    ``"AJCA-Albertino José Castanho Arteiro"`` while the acronym node is ``"AA"``.
    The name is derived from the header's own sigla separator rather than by
    stripping the acronym, so the real name survives instead of collapsing to the
    acronym. This is one of the name-drops the fix recovers across the corpus.
    """
    assert extract_teacher_info(F.soup("teacher_name_is_acronym")) == (
        "AA",
        "Albertino José Castanho Arteiro",
        481933,
    )


# ---------------------------------------------------------------------------
# -- class pages (turma_*) -> the full class-page parser set
# ---------------------------------------------------------------------------


def test_real_class_single_session_week_dates_range() -> None:
    assert extract_week_dates(F.soup("class_single_session")) == (
        date(2026, 2, 16),
        date(2026, 6, 1),
    )


def test_real_class_single_session_teachers_and_subjects() -> None:
    page = F.soup("class_single_session")

    assert extract_teachers(page) == [
        {"code": 95610, "acronym": "DEMEC_10", "name": "DEMEC_Monitor 1_DCM"},
    ]

    # NB: the third subject cell (schema field ``number``) is a large occurrence
    # id on real pages, not the small enrolment count the synthetic fixtures use.
    assert extract_subjects(page) == [
        {
            "code": "L.EM008",
            "name": "Desenho de Construção Mecânica",
            "acronym": "DCM",
            "number": 560352,
        },
    ]


def test_real_class_single_session_full_session() -> None:
    (session,) = extract_sessions(F.soup("class_single_session"))
    assert session == {
        "subject_acronym": "DCM",
        "weekday": WeekDay.MONDAY,
        "start_time": 1600,
        "duration": 4,
        "teachers": [95610],
        "classes": ["1LEM01", "1LEM02", "1LEM20"],
        "rooms": ["M107"],
        "type": "PL",
    }


def test_real_class_many_sessions_shape() -> None:
    page = F.soup("class_many_sessions")

    # A single-date week: start == end (the real analogue of the synthetic
    # "single date" parametrization in test_class_page).
    assert extract_week_dates(page) == (date(2026, 2, 16), date(2026, 2, 16))

    sessions = extract_sessions(page)
    assert len(sessions) == 19

    # First block, in document order, fully pinned.
    assert sessions[0] == {
        "subject_acronym": "TSTA II",
        "weekday": WeekDay.WEDNESDAY,
        "start_time": 830,
        "duration": 4,
        "teachers": [211120, 469850],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B034"],
        "type": "TP",
    }

    # The page mixes theoretical, theoretical-practical and lab typologies.
    assert {s["type"] for s in sessions} == {"T", "TP", "PL"}
    # Every session resolved a subject acronym and at least one teacher.
    assert all(s["subject_acronym"] for s in sessions)
    assert all(s["teachers"] for s in sessions)


def test_real_class_many_sessions_red_blocks_count() -> None:
    assert len(extract_red_blocks(F.soup("class_many_sessions"))) == 60


# ---------------------------------------------------------------------------
# -- room page (sala_*) -> extract_red_blocks
# ---------------------------------------------------------------------------


def test_real_room_red_blocks() -> None:
    red_blocks = extract_red_blocks(F.soup("room"))
    assert len(red_blocks) == 17
    # On this page every unavailable slot is on Saturday.
    assert {day for _time, day in red_blocks} == {WeekDay.SATURDAY}
    assert red_blocks[0] == (1400, WeekDay.SATURDAY)


# ---------------------------------------------------------------------------
# -- Scraper end-to-end over a real page (parser dispatch + agreement)
# ---------------------------------------------------------------------------


def test_real_get_class_page_end_to_end() -> None:
    """Drive the whole ``get_class_page`` dispatch over one real page.

    This is stronger than the per-parser asserts above: the session block's
    teacher acronym must resolve against the *same page's* teacher table, so a
    green result means the parsers agree with each other on real markup.
    """
    base = "https://mirror.example/"
    scraper = Scraper(base)
    scraper._session = FakeSession({base + "class.html": F.raw("class_single_session")})  # type: ignore[assignment]

    class_page = scraper.get_class_page("class.html")

    assert class_page["start_date"] == date(2026, 2, 16)
    assert class_page["end_date"] == date(2026, 6, 1)
    assert class_page["teachers"] == [
        {"code": 95610, "acronym": "DEMEC_10", "name": "DEMEC_Monitor 1_DCM"},
    ]
    assert len(class_page["sessions"]) == 1
    assert class_page["sessions"][0]["teachers"] == [95610]
    assert class_page["sessions"][0]["subject_acronym"] == "DCM"
    assert len(class_page["red_blocks"]) == 66


# ===========================================================================
# == Full-output golden pins for the richest real page (class_many_sessions)
# ===========================================================================
#
# The asserts above pin only the *first* element of each collection on this
# page (or an aggregate). A first-element pin cannot catch a parser regression
# that corrupts, drops, duplicates or reorders element N>0. The three tests
# below pin the page's teacher table, subject table and session grid in full,
# in document order — the "pin their *full* output" the module docstring
# promises, applied to the one fixture that actually exercises multi-row tables.

_MANY_TEACHERS = [
    {"code": 209614, "acronym": "APOC", "name": "António Pedro Oliveira de Carvalho"},
    {"code": 211120, "acronym": "CMB", "name": "Cidália Maria de Sousa Botelho"},
    {"code": 469850, "acronym": "CMMS", "name": "Cristina Maria Monteiro dos Santos"},
    {"code": 549820, "acronym": "ETPMC", "name": "Emanuel Tiago Pinto Monteiro da Costa"},
    {"code": 400655, "acronym": "JMMD", "name": "Joana Maia Moreira Dias"},
    {"code": 686046, "acronym": "JPSMF", "name": "João Pedro Soeiro de Matos Fernandes"},
    {"code": 553437, "acronym": "KIFG", "name": "Karla Isabel Freitas Gonçalves Jacinto"},
    {"code": 448318, "acronym": "LdN", "name": "Luciana Paiva das Neves"},
    # Two real teachers whose "name" is a system placeholder (M.EA.CAC.doc): the
    # parser must pass these through verbatim, not choke or normalise them.
    {"code": 98825, "acronym": "NAFV", "name": "M.EA.CAC.doc"},
    {"code": 98826, "acronym": "JMHC", "name": "M.EA.CAC1.doc"},
    {"code": 720807, "acronym": "MACT", "name": "Miguel Ângelo Cortez Teixeira"},
    {"code": 211751, "acronym": "MCV", "name": "Maria Cristina da Costa Vila"},
    {"code": 486363, "acronym": "PJRS", "name": "Paulo Jorge Rosa Santos"},
    {"code": 405047, "acronym": "PNMM", "name": "Pedro Nuno Meda Magalhães"},
    {"code": 354894, "acronym": "SCP", "name": "Sílvia Cardinal Pinho"},
    {"code": 350850, "acronym": "SV", "name": "Szabolcs Varga"},
    {"code": 533983, "acronym": "TJFF", "name": "Tiago João Fazeres Marques Ferradosa"},
    {"code": 420880, "acronym": "VJPV", "name": "Vítor Jorge Pais Vilar"},
]

_MANY_SUBJECTS = [
    {
        "code": "M.EA009",
        "name": "Laboratórios de Engenharia do Ambiente II",
        "acronym": "LEA II",
        "number": 559859,
    },
    {"code": "M.EA010", "name": "Acústica Ambiental", "acronym": "AA", "number": 559860},
    {
        "code": "M.EA011",
        "name": "Direito e Economia do Ambiente",
        "acronym": "DEA",
        "number": 559861,
    },
    {
        "code": "M.EA012",
        "name": "Climatologia e Alterações Climáticas",
        "acronym": "CAC",
        "number": 559862,
    },
    {
        "code": "M.EA014",
        "name": "Fundamentos de Mecânica dos Fluidos",
        "acronym": "FMF",
        "number": 559864,
    },
    {
        "code": "M.EA015",
        "name": "Análise Quantitativa de Risco Ambiental",
        "acronym": "AQRA",
        "number": 559865,
    },
    {
        "code": "M.EA017",
        "name": "Instalações Industriais e Construções Civis",
        "acronym": "IICC",
        "number": 559866,
    },
    {
        "code": "M.EA018",
        "name": "Tecnologias e Sistemas de Tratamento de Águas II",
        "acronym": "TSTA II",
        "number": 559867,
    },
    {
        "code": "M.EA019",
        "name": "Tecnologias e Sistemas de Tratamento de Resíduos Sólidos II",
        "acronym": "TSTRS II",
        "number": 559868,
    },
    {
        "code": "M.EC014",
        "name": "Hidráulica Marítima e Costeira",
        "acronym": "HMC",
        "number": 560455,
    },
]

_MANY_SESSIONS = [
    {
        "subject_acronym": "TSTA II",
        "weekday": WeekDay.WEDNESDAY,
        "start_time": 830,
        "duration": 4,
        "teachers": [211120, 469850],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B034"],
        "type": "TP",
    },
    {
        "subject_acronym": "IICC",
        "weekday": WeekDay.MONDAY,
        "start_time": 900,
        "duration": 3,
        "teachers": [405047],
        "classes": ["M.EA101", "M.EA102", "M.EA103", "M.EQ01_IICC"],
        "rooms": ["B022"],
        "type": "TP",
    },
    {
        "subject_acronym": "FMF",
        "weekday": WeekDay.TUESDAY,
        "start_time": 900,
        "duration": 3,
        "teachers": [553437],
        "classes": ["L.EA 201", "M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B033"],
        "type": "TP",
    },
    {
        "subject_acronym": "TSTA II",
        "weekday": WeekDay.FRIDAY,
        "start_time": 900,
        "duration": 3,
        "teachers": [211120, 469850],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B021"],
        "type": "TP",
    },
    {
        "subject_acronym": "TSTRS II",
        "weekday": WeekDay.MONDAY,
        "start_time": 1030,
        "duration": 3,
        "teachers": [400655, 354894],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B012"],
        "type": "TP",
    },
    {
        "subject_acronym": "TSTRS II",
        "weekday": WeekDay.TUESDAY,
        "start_time": 1030,
        "duration": 4,
        "teachers": [400655],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B033"],
        "type": "TP",
    },
    {
        "subject_acronym": "IICC",
        "weekday": WeekDay.WEDNESDAY,
        "start_time": 1030,
        "duration": 4,
        "teachers": [405047],
        "classes": ["M.EA101", "M.EA102", "M.EA103", "M.EQ01_IICC"],
        "rooms": ["B016"],
        "type": "TP",
    },
    {
        "subject_acronym": "CAC",
        "weekday": WeekDay.FRIDAY,
        "start_time": 1030,
        "duration": 4,
        "teachers": [98825, 98826],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B011"],
        "type": "TP",
    },
    {
        "subject_acronym": "FMF",
        "weekday": WeekDay.THURSDAY,
        "start_time": 1130,
        "duration": 3,
        "teachers": [720807, 350850],
        "classes": [
            "L.EA 201",
            "L.EA 202",
            "L.EA 203",
            "L.EA 204",
            "M.EA101",
            "M.EA102",
            "M.EA103",
        ],
        "rooms": ["B005"],
        "type": "T",
    },
    {
        "subject_acronym": "AQRA",
        "weekday": WeekDay.TUESDAY,
        "start_time": 1330,
        "duration": 3,
        "teachers": [211751],
        "classes": ["M.EA101", "M.EA102", "M.EA103", "M.EQ01_AMB"],
        "rooms": ["B016"],
        "type": "TP",
    },
    {
        "subject_acronym": "FMF",
        "weekday": WeekDay.WEDNESDAY,
        "start_time": 1330,
        "duration": 3,
        "teachers": [720807, 350850],
        "classes": [
            "L.EA 201",
            "L.EA 202",
            "L.EA 203",
            "L.EA 204",
            "M.EA101",
            "M.EA102",
            "M.EA103",
        ],
        "rooms": ["B019"],
        "type": "T",
    },
    {
        "subject_acronym": "HMC",
        "weekday": WeekDay.FRIDAY,
        "start_time": 1330,
        "duration": 3,
        "teachers": [448318, 486363, 533983],
        "classes": ["12M.ECH1", "M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B222"],
        "type": "TP",
    },
    {
        "subject_acronym": "AA",
        "weekday": WeekDay.MONDAY,
        "start_time": 1400,
        "duration": 2,
        "teachers": [209614],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B021"],
        "type": "T",
    },
    {
        "subject_acronym": "DEA",
        "weekday": WeekDay.THURSDAY,
        "start_time": 1430,
        "duration": 4,
        "teachers": [686046, 533983],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B024"],
        "type": "TP",
    },
    {
        "subject_acronym": "AA",
        "weekday": WeekDay.MONDAY,
        "start_time": 1500,
        "duration": 4,
        "teachers": [209614],
        "classes": ["M.EA101"],
        "rooms": ["B225"],
        "type": "TP",
    },
    {
        "subject_acronym": "LEA II",
        "weekday": WeekDay.TUESDAY,
        "start_time": 1500,
        "duration": 6,
        "teachers": [469850, 549820, 400655, 211751, 420880],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B012"],
        "type": "PL",
    },
    {
        "subject_acronym": "AQRA",
        "weekday": WeekDay.WEDNESDAY,
        "start_time": 1500,
        "duration": 4,
        "teachers": [211751],
        "classes": ["M.EA101", "M.EA102", "M.EA103", "M.EQ01_AMB"],
        "rooms": ["B028"],
        "type": "TP",
    },
    {
        "subject_acronym": "AA",
        "weekday": WeekDay.FRIDAY,
        "start_time": 1500,
        "duration": 2,
        "teachers": [209614],
        "classes": ["M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B021"],
        "type": "T",
    },
    {
        "subject_acronym": "HMC",
        "weekday": WeekDay.THURSDAY,
        "start_time": 1630,
        "duration": 4,
        "teachers": [448318, 486363, 533983],
        "classes": ["12M.ECH1", "M.EA101", "M.EA102", "M.EA103"],
        "rooms": ["B332"],
        "type": "T",
    },
]


def test_real_class_many_sessions_all_teachers() -> None:
    """Pin the full 18-row teacher table (accented + placeholder names, in order)."""
    assert extract_teachers(F.soup("class_many_sessions")) == _MANY_TEACHERS


def test_real_class_many_sessions_all_subjects() -> None:
    """Pin the full 10-row subject table, including the large occurrence-id ``number``."""
    assert extract_subjects(F.soup("class_many_sessions")) == _MANY_SUBJECTS


def test_real_class_many_sessions_all_sessions() -> None:
    """Pin every one of the 19 session blocks in full document order.

    Complements ``test_real_class_many_sessions_shape`` (which only asserts
    aggregates): here a single wrong weekday, duration, teacher id, room or class
    on any block surfaces as an exact diff.
    """
    assert extract_sessions(F.soup("class_many_sessions")) == _MANY_SESSIONS


def test_real_class_many_sessions_tipologia_map() -> None:
    """The legend on a real multi-typology page maps three colour classes."""
    assert extract_tipologia_map(F.soup("class_many_sessions")) == {
        "td_tipologia_21": "TP",
        "td_tipologia_19": "T",
        "td_tipologia_17": "PL",
    }


# ===========================================================================
# == False-positive guards: full collections, not just element [0]
# ===========================================================================
#
# The pinned counts above catch *under*-extraction (a dropped row). These guard
# the other direction — phantom rows, duplicated entries, malformed values — by
# asserting structural invariants across the *whole* real collection.


@pytest.mark.parametrize(
    ("fixture", "expected_count"),
    [
        ("teacher_normal", 27),
        ("room", 17),
        ("class_single_session", 66),
        ("class_many_sessions", 60),
    ],
)
def test_real_red_blocks_are_wellformed_and_deduplicated(
    fixture: str,
    expected_count: int,
) -> None:
    """Every real red-block set has the exact size, no duplicate ``(time, day)``
    (a duplicate would mean one grid cell was counted twice, or two cells mapped
    to the same slot), a valid HHMM ``time`` and a real ``WeekDay``."""
    red_blocks = extract_red_blocks(F.soup(fixture))

    assert len(red_blocks) == expected_count
    # No double-counting: a (time, day) pair identifies at most one grid cell.
    assert len(set(red_blocks)) == expected_count
    for time, day in red_blocks:
        assert isinstance(day, WeekDay)
        assert isinstance(time, int)
        assert 0 <= time <= 2359
        assert time % 100 < 60  # a real HHMM minute component, never e.g. 1470


def test_real_teacher_normal_red_blocks_day_distribution() -> None:
    """Pin the per-day spread, not just the total: 17 Saturday slots plus two on
    each weekday. Because the five weekday buckets are all 2, this only catches a
    mapping bug that moves blocks to or from the Saturday column (17); a swap
    between two weekdays leaves the distribution unchanged."""
    red_blocks = extract_red_blocks(F.soup("teacher_normal"))
    per_day = Counter(day for _time, day in red_blocks)
    assert per_day == {
        WeekDay.SATURDAY: 17,
        WeekDay.MONDAY: 2,
        WeekDay.TUESDAY: 2,
        WeekDay.WEDNESDAY: 2,
        WeekDay.THURSDAY: 2,
        WeekDay.FRIDAY: 2,
    }


@pytest.mark.parametrize(
    ("fixture", "expected_per_day"),
    [
        (
            "class_single_session",
            {
                WeekDay.SATURDAY: 29,
                WeekDay.TUESDAY: 17,
                WeekDay.MONDAY: 5,
                WeekDay.WEDNESDAY: 5,
                WeekDay.THURSDAY: 5,
                WeekDay.FRIDAY: 5,
            },
        ),
        (
            "class_many_sessions",
            {
                WeekDay.SATURDAY: 29,
                WeekDay.WEDNESDAY: 11,
                WeekDay.MONDAY: 5,
                WeekDay.TUESDAY: 5,
                WeekDay.THURSDAY: 5,
                WeekDay.FRIDAY: 5,
            },
        ),
    ],
)
def test_real_class_page_red_blocks_day_distribution(
    fixture: str,
    expected_per_day: dict[WeekDay, int],
) -> None:
    """Pin the per-day red-block spread on both class pages, not just the total.

    ``test_real_red_blocks_are_wellformed_and_deduplicated`` only asserts the
    *count* (66 / 60) for these pages, so a column→weekday mapping bug that
    shuffled blocks between days while keeping the total would slip through. This
    is the false-positive guard the ``room`` (full list) and ``teacher_normal``
    (distribution) fixtures already have, extended to the two class grids."""
    red_blocks = extract_red_blocks(F.soup(fixture))
    per_day = Counter(day for _time, day in red_blocks)
    assert dict(per_day) == expected_per_day


_SATURDAY_HALF_HOURS = [
    1400,
    1430,
    1500,
    1530,
    1600,
    1630,
    1700,
    1730,
    1800,
    1830,
    1900,
    1930,
    2000,
    2030,
    2100,
    2130,
    2200,
]


def test_real_room_red_blocks_full_list() -> None:
    """Pin the room's entire red-block list: a contiguous Saturday afternoon/evening
    block from 14:00 to 22:00 in half-hour steps."""
    assert extract_red_blocks(F.soup("room")) == [
        (time, WeekDay.SATURDAY) for time in _SATURDAY_HALF_HOURS
    ]


def test_real_menu_teacher_links_all_wellformed() -> None:
    """All 661 links are distinct and shaped like a teacher page — no phantom,
    blank or duplicated entry slipped in (element [0] alone cannot show this)."""
    teachers_li, _, _ = extract_menu_tags(F.soup("menu"))
    links = extract_teacher_links(teachers_li)

    assert len(links) == 661
    assert len(set(links)) == 661  # no duplicate department link
    assert all(link.startswith("docente_") for link in links)
    assert all(link.endswith(".html") for link in links)


def test_real_menu_degrees_structural_invariants() -> None:
    """Structural invariants over the whole 51-degree tree: unique acronyms, the
    exact year/class/week-link totals, and no class left without a page link."""
    _, classes_li, _ = extract_menu_tags(F.soup("menu"))
    degrees = extract_sessions_info(classes_li)

    assert len(degrees) == 51
    assert len({d["acronym"] for d in degrees}) == 51  # acronyms are unique

    years = [year for d in degrees for year in d["years"]]
    all_classes = [c for year in years for c in year["classes"]]
    all_links = [link for c in all_classes for link in c["links"]]

    assert len(years) == 74
    assert len(all_classes) == 448
    assert len(all_links) == 745

    assert all(isinstance(y["number"], int) and y["number"] >= 1 for y in years)
    assert all(c["code"] for c in all_classes)  # no blank class code
    assert all(c["links"] for c in all_classes)  # every class has >= 1 week link
    assert all(c["pages"] == [] for c in all_classes)  # pages populated later, not here


def test_real_menu_rooms_registry_split_and_links() -> None:
    """Across all 149 rooms: names are unique, every room carries a timetable
    link, and the registry lookup partitions them 91 known / 58 fallback — the
    both-branches split the single ``rooms[0]``/``rooms[-1]`` pin only samples."""
    _, _, rooms_li = extract_menu_tags(F.soup("menu"))
    rooms = extract_rooms_info(rooms_li)

    assert len(rooms) == 149
    assert len({r["name"] for r in rooms}) == 149
    assert all(r["link"] for r in rooms)

    known = [r for r in rooms if r["type_"] != "Desconhecido"]
    unknown = [r for r in rooms if r["type_"] == "Desconhecido"]
    assert len(known) == 91
    assert len(unknown) == 58
    # An unknown room falls back to "Desconhecido" on *every* metadata field.
    assert all(r["size"] == "Desconhecido" and r["seats"] == "Desconhecido" for r in unknown)


@pytest.mark.parametrize("fixture", ["class_single_session", "class_many_sessions"])
def test_real_class_page_sessions_agree_with_page_tables(fixture: str) -> None:
    """Every session on a real page resolves against that *same* page's tables.

    A session's teacher ids must all appear in the page's teacher table and its
    subject acronym in the page's subject table; each session must also carry a
    valid start time, a non-empty class list and at least one teacher. This pins
    cross-parser agreement over the *full* real session set (the single
    ``get_class_page`` end-to-end only exercises the one-session page)."""
    page = F.soup(fixture)
    sessions = extract_sessions(page)
    teacher_codes = {t["code"] for t in extract_teachers(page)}
    subject_acronyms = {s["acronym"] for s in extract_subjects(page)}

    assert sessions  # both pages have at least one session
    for session in sessions:
        assert session["teachers"], "a session with no teacher is a parse failure"
        assert set(session["teachers"]) <= teacher_codes
        assert session["subject_acronym"] in subject_acronyms
        assert session["classes"]  # never an empty class list
        assert session["rooms"]  # ["Online"] when remote, never []
        assert 0 <= session["start_time"] <= 2359
        assert session["duration"] >= 1


# ===========================================================================
# == Scraper dispatch over real bytes (completing get_class_page's siblings)
# ===========================================================================
#
# ``test_real_get_class_page_end_to_end`` grounds one of the four Scraper page
# fetchers on real bytes. These cover the other three, so every public Scraper
# entry point is exercised end-to-end against a captured page, not just its
# underlying parser in isolation.


def test_real_read_menu_end_to_end() -> None:
    """``read_menu`` chains two real GETs: root frameset -> menu frame it names.

    Proves the frameset's ``%3F``-encoded ``extract_menu_link`` result is fed
    back verbatim as the second request path, and that all three menu sections
    parse from the real menu bytes in one pass."""
    base = "https://mirror.example/"
    menu_path = "coluna1.html%3F639044378190378436.html"
    session = FakeSession(
        {
            base: F.raw("frameset"),
            base + menu_path: F.raw("menu"),
        },
    )
    scraper = Scraper(base)
    scraper._session = session  # type: ignore[assignment]

    teacher_links, degrees, rooms = scraper.read_menu()

    assert len(teacher_links) == 661
    assert len(degrees) == 51
    assert len(rooms) == 149
    assert [url for url, _ in session.calls] == [base, base + menu_path]


def test_real_get_teacher_page_end_to_end() -> None:
    """``get_teacher_page`` fuses ``extract_teacher_info`` + ``extract_red_blocks``
    into one ``TeacherInfo`` over a real teacher page."""
    base = "https://mirror.example/"
    scraper = Scraper(base)
    scraper._session = FakeSession({base + "teacher.html": F.raw("teacher_normal")})  # type: ignore[assignment]

    teacher = scraper.get_teacher_page("teacher.html")

    assert teacher["acronym"] == "JCR"
    assert teacher["name"] == "José Pedro Coelho Rodrigues"
    assert teacher["code"] == 415643
    assert len(teacher["red_blocks"]) == 27
    assert teacher["red_blocks"][0] == (800, WeekDay.MONDAY)


def test_real_get_room_page_end_to_end() -> None:
    """``get_room_page`` returns the real room's red blocks straight through."""
    base = "https://mirror.example/"
    scraper = Scraper(base)
    scraper._session = FakeSession({base + "room.html": F.raw("room")})  # type: ignore[assignment]

    red_blocks = scraper.get_room_page("room.html")

    assert len(red_blocks) == 17
    assert {day for _time, day in red_blocks} == {WeekDay.SATURDAY}


# ===========================================================================
# == Pipeline logic grounded on real inputs (manager, not just the parsers)
# ===========================================================================
#
# Every test above stops at the parser boundary. The manager that turns parsed
# pages into DB rows is only ever driven by hand-built synthetic pages (see
# tests/integration/test_ingestion_manager.py), so no real captured value ever
# reaches the pipeline transforms. ``_compute_weeks`` is the one transform that
# needs no database — it expands a page's ``cabtitulo`` date range into weekly
# start dates — so it can be grounded directly on the real ranges the parsers
# read, closing part of that gap. The two fixtures bracket both regimes: a
# multi-month range and a degenerate single-date week (start == end).


@pytest.mark.parametrize(
    ("fixture", "expected_weeks"),
    [
        # 2026-02-16 .. 2026-06-01: a full semester of Mondays, endpoint included.
        ("class_single_session", 16),
        # start == end: exactly one week, never zero (the boundary is inclusive).
        ("class_many_sessions", 1),
    ],
)
def test_real_compute_weeks_over_real_date_ranges(fixture: str, expected_weeks: int) -> None:
    """Drive the manager's week expansion over the real parsed date ranges.

    Pins that ``_compute_weeks`` turns a real ``(start_date, end_date)`` into the
    expected number of weekly start dates, that the first week is the real start
    and the last never overruns the real end, and that every step is exactly 7
    days. A regression that made the range end-exclusive, or stepped by something
    other than a week, would surface here against real data rather than only
    synthetic. (The weeks land on Mondays only because both real ``start_date``
    values do; ``_compute_weeks`` steps from ``start_date``, it never aligns to a
    weekday.)"""
    start_date, end_date = extract_week_dates(F.soup(fixture))
    weeks = IngestionManager._compute_weeks({"start_date": start_date, "end_date": end_date})

    assert len(weeks) == expected_weeks
    assert weeks[0] == start_date
    assert weeks[-1] <= end_date
    assert all(week.weekday() == 0 for week in weeks)  # real start_date is a Monday; step keeps it
    assert all((b - a) == timedelta(weeks=1) for a, b in pairwise(weeks))
