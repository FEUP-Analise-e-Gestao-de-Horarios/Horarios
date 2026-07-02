"""Integration tests for :class:`src.ingestion.manager.IngestionManager`.

These drive the *whole* ingestion pipeline against a real per-project SQLite
file, with only the HTTP boundary faked. A ``_FakeScraper`` returns a small but
internally-consistent dataset — one degree, one year, two classes sharing a
subject, a menu teacher plus a class-page-only teacher, one room, and sessions
spanning two weeks — so every phase runs for real:

* teachers (incl. the merge of class-page teachers missing from the menu),
* degrees / years / classes,
* rooms + red blocks,
* subjects + sessions (incl. the multi-class session-reuse branch),
* shift assignment, and
* content-fingerprint block-id reassignment across weeks.

The manager opens its *own* session on the project DB; assertions query through
a fresh session so they observe the committed result, not the fixture's state.
"""

import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.ingestion import manager as manager_module
from src.ingestion.manager import IngestionManager
from src.projects.models import Project
from src.projects.projects_db.models import (
    Class,
    ClassRedBlock,
    Degree,
    Room,
    RoomRedBlock,
    Subject,
    Teacher,
    TeacherRedBlock,
    Year,
)
from src.projects.projects_db.models import Session as SessionModel
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session
from src.projects.projects_db.schemas.weekday import WeekDay

WEEK_1 = datetime.date(2025, 9, 15)
WEEK_2 = datetime.date(2025, 9, 22)


# ---------------------------------------------------------------------------
# -- Canned scrape data
# ---------------------------------------------------------------------------


def _t_session(subject, weekday, start, duration, teachers, classes, rooms, type_):
    return {
        "subject_acronym": subject,
        "weekday": weekday,
        "start_time": start,
        "duration": duration,
        "teachers": teachers,
        "classes": classes,
        "rooms": rooms,
        "type": type_,
    }


PROG = {"code": "L.EIC001", "name": "Programação", "acronym": "PROG", "number": 120}

# 1LEIC01: a T block, a single-class TP block, and a multi-class TP block.
_PAGE_1LEIC01 = {
    "start_date": WEEK_1,
    "end_date": WEEK_2,
    "teachers": [
        {"code": 123, "acronym": "ABC", "name": "Ada"},
        {"code": 456, "acronym": "DEF", "name": "Duarte"},  # not in the menu
    ],
    "subjects": [PROG],
    "sessions": [
        _t_session("PROG", WeekDay.MONDAY, 900, 2, [123], ["1LEIC01"], ["B001"], "T"),
        _t_session("PROG", WeekDay.MONDAY, 1400, 2, [456], ["1LEIC01"], ["B001"], "TP"),
        _t_session("PROG", WeekDay.MONDAY, 1600, 2, [123], ["1LEIC01", "1LEIC02"], ["B001"], "TP"),
    ],
    "red_blocks": [(1000, WeekDay.MONDAY)],
}

# 1LEIC02: an online T block, plus the same multi-class TP block (reused).
_PAGE_1LEIC02 = {
    "start_date": WEEK_1,
    "end_date": WEEK_2,
    "teachers": [{"code": 123, "acronym": "ABC", "name": "Ada"}],
    "subjects": [PROG],
    "sessions": [
        _t_session("PROG", WeekDay.MONDAY, 900, 2, [123], ["1LEIC02"], ["Online"], "T"),
        _t_session("PROG", WeekDay.MONDAY, 1600, 2, [123], ["1LEIC01", "1LEIC02"], ["B001"], "TP"),
    ],
    "red_blocks": [],
}

_DEGREES = [
    {
        "acronym": "LEIC",
        "name": "Licenciatura em Engenharia Informatica",
        "years": [
            {
                "number": 1,
                "classes": [
                    {"code": "1LEIC01", "links": ["c1.html"], "pages": []},
                    {"code": "1LEIC02", "links": ["c2.html"], "pages": []},
                ],
            },
        ],
    },
]

_ROOMS = [
    {"name": "B001", "type_": "Anf", "size": "Queijo", "seats": "N/A", "link": "r/b001.html"},
]


class _FakeScraper:
    """A drop-in for :class:`Scraper` returning canned data; records ``close``."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False

    def read_menu(self):
        # A fresh copy per call so the manager's in-place page loading never
        # leaks across tests.
        import copy

        return (["t/abc.html"], copy.deepcopy(_DEGREES), copy.deepcopy(_ROOMS))

    def get_teacher_page(self, path: str):
        return {
            "acronym": "ABC",
            "name": "Ada",
            "code": 123,
            "red_blocks": [(900, WeekDay.MONDAY)],
        }

    def get_class_page(self, link: str):
        import copy

        return copy.deepcopy(_PAGE_1LEIC01 if link == "c1.html" else _PAGE_1LEIC02)

    def get_room_page(self, path: str):
        return [(1100, WeekDay.MONDAY)]

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_scraper(monkeypatch: pytest.MonkeyPatch) -> _FakeScraper:
    """Patch the manager's ``Scraper`` symbol to build our fake and expose it."""
    created: list[_FakeScraper] = []

    def factory(url: str) -> _FakeScraper:
        scraper = _FakeScraper(url)
        created.append(scraper)
        return scraper

    monkeypatch.setattr(manager_module, "Scraper", factory)
    # The manager constructs the scraper lazily in __init__; return a proxy that
    # resolves to the single instance once it exists.
    return created  # type: ignore[return-value]


def _fresh_session(project_id: int) -> Session:
    return get_session(general_db(project_id))


# ---------------------------------------------------------------------------
# -- Happy path
# ---------------------------------------------------------------------------


def test_run_populates_all_entities(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        assert db.scalar(select(func.count()).select_from(Degree)) == 1
        assert db.scalar(select(func.count()).select_from(Year)) == 1
        assert db.scalar(select(func.count()).select_from(Class)) == 2
        assert db.scalar(select(func.count()).select_from(Subject)) == 1
        assert db.scalar(select(func.count()).select_from(Teacher)) == 2
        assert db.scalar(select(func.count()).select_from(Room)) == 1
    finally:
        db.close()


def test_run_ingests_red_blocks(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        assert db.scalar(select(func.count()).select_from(TeacherRedBlock)) == 1
        assert db.scalar(select(func.count()).select_from(RoomRedBlock)) == 1
        # Class red blocks come from the first page only; 1LEIC01 has one.
        assert db.scalar(select(func.count()).select_from(ClassRedBlock)) == 1
    finally:
        db.close()


def test_run_creates_sessions_spanning_two_weeks(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        # 4 distinct blocks (T@900 1LEIC01, TP@1400 1LEIC01, TP@1600 shared,
        # T@900 1LEIC02-online), each present in both weeks -> 8 session rows.
        assert db.scalar(select(func.count()).select_from(SessionModel)) == 8
        distinct_blocks = db.scalar(
            select(func.count(func.distinct(SessionModel.original_block_id))),
        )
        assert distinct_blocks == 4
        weeks = set(db.scalars(select(SessionModel.week.distinct())).all())
        assert weeks == {WEEK_1, WEEK_2}
    finally:
        db.close()


def test_run_online_session_has_no_room(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        # The 1LEIC02 T@900 block is "Online": its two sessions have no rooms.
        online = db.scalars(
            select(SessionModel).where(
                SessionModel.type == "T",
                SessionModel.start_time == 900,
            ),
        ).all()
        online_no_room = [s for s in online if not s.rooms]
        assert len(online_no_room) == 2
    finally:
        db.close()


def test_run_multiclass_session_links_both_classes(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        # The shared TP@1600 block is one session per week, each linked to both
        # classes via session_class_subjects (reuse branch, not a duplicate).
        shared = db.scalars(
            select(SessionModel).where(SessionModel.start_time == 1600),
        ).all()
        assert len(shared) == 2
        for session in shared:
            class_ids = {scs.class_id for scs in session.session_class_subjects}
            assert len(class_ids) == 2
    finally:
        db.close()


def test_run_assigns_shifts_to_theoretical_classes(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    db = _fresh_session(project.pk)
    try:
        shifts = {c.code: c.shift for c in db.scalars(select(Class)).all()}
        # Both classes have a T session, so both leave the initial shift 0.
        assert shifts["1LEIC01"] >= 1
        assert shifts["1LEIC02"] >= 1
    finally:
        db.close()


def test_run_marks_project_finished_and_snapshots_db(
    project: Project,
    project_db: Session,
    fake_scraper: list,
) -> None:
    with IngestionManager(proj_id=project.pk) as m:
        m.run()

    project.refresh_from_db()
    assert project.ingestion_started_at is not None
    assert project.ingestion_finished_at is not None
    assert project.ingestion_failed_at is None
    # The success path snapshots general_database.db to initial_database.db.
    assert initial_db(project.pk).exists()
    # The single fake scraper was closed on teardown.
    assert fake_scraper[0].closed is True


# ---------------------------------------------------------------------------
# -- Failure path & construction
# ---------------------------------------------------------------------------


def test_run_failure_marks_project_failed_and_reraises(
    project: Project,
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BoomScraper(_FakeScraper):
        def get_class_page(self, link: str):
            raise RuntimeError("scrape exploded")

    monkeypatch.setattr(manager_module, "Scraper", _BoomScraper)

    with (
        pytest.raises(RuntimeError, match="scrape exploded"),
        IngestionManager(
            proj_id=project.pk,
        ) as m,
    ):
        m.run()

    project.refresh_from_db()
    assert project.ingestion_failed_at is not None
    assert project.ingestion_finished_at is None


def test_construct_unknown_project_raises(db: None) -> None:
    with pytest.raises(Project.DoesNotExist):
        IngestionManager(proj_id=999_999)
