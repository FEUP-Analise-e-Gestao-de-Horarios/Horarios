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

from datetime import date

from src.ingestion.parsers.class_page import (
    extract_sessions,
    extract_subjects,
    extract_teachers,
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


def test_real_teacher_name_is_dropped_when_prefix_differs_from_acronym() -> None:
    """KNOWN WART, pinned as current behaviour (not endorsed).

    On this real page the ``cabtitulo`` first node is
    ``"AJCA-Albertino José Castanho Arteiro"`` while the acronym node is ``"AA"``.
    ``extract_teacher_info`` derives the name by stripping the *acronym* prefix
    off the first node; because the leading token ("AJCA") is not the acronym
    ("AA") and the separator is a bare "-" (not " - "), the strip fails and the
    name falls back to the acronym. The real name is therefore lost.

    This is one of 25 such name-drops in the captured corpus. If the parser is
    fixed to recover the name, update this assertion — the change is the point.
    """
    assert extract_teacher_info(F.soup("teacher_name_is_acronym")) == ("AA", "AA", 481933)


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


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass


class _FakeSession:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def get(self, url: str, timeout: object = None) -> _FakeResponse:
        return _FakeResponse(self._content)

    def close(self) -> None:
        pass


def test_real_get_class_page_end_to_end() -> None:
    """Drive the whole ``get_class_page`` dispatch over one real page.

    This is stronger than the per-parser asserts above: the session block's
    teacher acronym must resolve against the *same page's* teacher table, so a
    green result means the parsers agree with each other on real markup.
    """
    scraper = Scraper("https://mirror.example/")
    scraper._session = _FakeSession(F.raw("class_single_session"))  # type: ignore[assignment]

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
