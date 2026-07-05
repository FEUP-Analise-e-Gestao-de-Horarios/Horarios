"""Integration tests for the project *sessions* endpoint.

The single route is covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/sessions/?year_id=<uuid>`` — the year-scoped session
  blocks view, with optional ``subject_ids``, ``class_ids`` and ``weekdays``
  filters (repeated query keys for list params).

Assertions target the ``SuccessResponse`` envelope and the ``WeekBlock`` wire
shape. Query-param validation, the year/subject/class existence checks and the
weekday filter are all exercised. Order-independent facts are compared as sets;
the volatile ``timestamp`` is only checked for presence.
"""

import datetime
import uuid

import pytest
from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    link_session_room,
    link_session_teacher,
    make_class,
    make_degree,
    make_room,
    make_session,
    make_session_class_subject,
    make_subject,
    make_teacher,
    make_year,
)


def _sessions_url(project_id: int, query: str = "") -> str:
    return f"/api/projects/{project_id}/sessions/{query}"


def _stats_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/stats"


# ---------------------------------------------------------------------------
# -- Auth / project decorators
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_sessions_url(project.pk, f"?year_id={uuid.uuid7()}"))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(
        _sessions_url(project.pk + 1000, f"?year_id={uuid.uuid7()}"),
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


# ---------------------------------------------------------------------------
# -- Query-param validation
# ---------------------------------------------------------------------------


def test_missing_year_id_returns_400(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_sessions_url(project.pk))
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_invalid_year_id_returns_400(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_sessions_url(project.pk, "?year_id=not-a-uuid"))
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_unknown_year_id_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_sessions_url(project.pk, f"?year_id={uuid.uuid7()}"))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.years.not_found"


def test_subject_id_not_in_year_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db)

    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&subject_ids={uuid.uuid7()}"),
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.subjects.not_found"


def test_class_id_not_in_year_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db)

    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&class_ids={uuid.uuid7()}"),
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.classes.not_found"


# ---------------------------------------------------------------------------
# -- Happy path & filters
# ---------------------------------------------------------------------------


def test_empty_year_returns_no_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db)

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))

    assert response.status_code == 200
    assert response.json()["data"]["blocks"] == []


def test_returns_block_with_seeded_session(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    session_row = make_session(project_db, weekday=WeekDay.MONDAY)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    block = blocks[0]
    assert len(block["sessions"]) == 1
    session = block["sessions"][0]
    assert session["id"] == str(session_row.id)
    assert session["weekday"] == "monday"
    assert {c["code"] for c in session["classes"]} == {"1LEIC01"}
    assert {s["id"] for s in session["subjects"]} == {str(subject.id)}


def test_weekdays_filter_restricts_to_matching_days(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    monday_session = make_session(project_db, weekday=WeekDay.MONDAY)
    tuesday_session = make_session(project_db, weekday=WeekDay.TUESDAY)
    for session_row in (monday_session, tuesday_session):
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )

    # No filter: both sessions land in the same week, hence one block.
    unfiltered = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))
    assert unfiltered.status_code == 200
    unfiltered_blocks = unfiltered.json()["data"]["blocks"]
    assert len(unfiltered_blocks) == 1
    weekdays = {s["weekday"] for s in unfiltered_blocks[0]["sessions"]}
    assert weekdays == {"monday", "tuesday"}

    # Filtered to Monday: only the Monday session remains.
    filtered = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&weekdays=monday"),
    )
    assert filtered.status_code == 200
    filtered_blocks = filtered.json()["data"]["blocks"]
    assert len(filtered_blocks) == 1
    filtered_sessions = filtered_blocks[0]["sessions"]
    assert len(filtered_sessions) == 1
    assert filtered_sessions[0]["id"] == str(monday_session.id)
    assert filtered_sessions[0]["weekday"] == "monday"


# ---------------------------------------------------------------------------
# -- Week-block grouping (fingerprint -> group -> representative)
# ---------------------------------------------------------------------------


def test_identical_consecutive_weeks_collapse_into_one_block(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Same class/subject taught with an identical timetable in two adjacent
    # weeks: contiguous equal fingerprints collapse into a single block whose
    # ``weeks`` list carries both dates (hits week_blocks.py:74).
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)
    for week in (week_a, week_b):
        session_row = make_session(
            project_db,
            week=week,
            weekday=WeekDay.MONDAY,
            start_time=9,
            duration=2,
            type="T",
        )
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    block = blocks[0]
    assert block["weeks"] == ["2025-09-15", "2025-09-22"]
    # The block renders a single representative week (the first).
    assert len(block["sessions"]) == 1
    assert block["sessions"][0]["week"] == "2025-09-15"


def test_differing_weeks_produce_separate_blocks_with_correct_weeks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Two weeks whose timetables differ (different start times) must NOT
    # collapse: each becomes its own block carrying its own single-date
    # ``weeks`` list, in chronological order.
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)
    session_a = make_session(project_db, week=week_a, start_time=9)
    session_b = make_session(project_db, week=week_b, start_time=11)
    for session_row in (session_a, session_b):
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 2

    first, second = blocks
    assert first["weeks"] == ["2025-09-15"]
    assert second["weeks"] == ["2025-09-22"]
    assert [s["id"] for s in first["sessions"]] == [str(session_a.id)]
    assert [s["id"] for s in second["sessions"]] == [str(session_b.id)]
    assert first["sessions"][0]["start_time"] == 9
    assert second["sessions"][0]["start_time"] == 11


def test_block_session_enriches_teachers_rooms_and_dedupes_subjects(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A single session with two teachers, two rooms, and two class/subject rows
    # that share one subject: the wire session carries both teacher and room
    # ids, both classes, and exactly one (deduped) subject.
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    teacher_a = make_teacher(project_db, acronym="AAA", name="Teacher A")
    teacher_b = make_teacher(project_db, acronym="BBB", name="Teacher B")
    room_a = make_room(project_db, name="B001")
    room_b = make_room(project_db, name="B002")

    session_row = make_session(project_db, weekday=WeekDay.MONDAY)
    link_session_teacher(project_db, session_row=session_row, teacher=teacher_a)
    link_session_teacher(project_db, session_row=session_row, teacher=teacher_b)
    link_session_room(project_db, session_row=session_row, room=room_a)
    link_session_room(project_db, session_row=session_row, room=room_b)
    for class_row in (class_a, class_b):
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
        )

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year.id}"))

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    assert len(blocks[0]["sessions"]) == 1
    session = blocks[0]["sessions"][0]
    assert session["id"] == str(session_row.id)
    assert {t["id"] for t in session["teachers"]} == {str(teacher_a.id), str(teacher_b.id)}
    assert {r["id"] for r in session["rooms"]} == {str(room_a.id), str(room_b.id)}
    # One shared subject across two class rows -> deduped to a single subject.
    assert {s["id"] for s in session["subjects"]} == {str(subject.id)}
    assert {c["id"] for c in session["classes"]} == {str(class_a.id), str(class_b.id)}
    assert {c["code"] for c in session["classes"]} == {"1LEIC01", "1LEIC02"}


# ---------------------------------------------------------------------------
# -- Filters (narrowing effect) & isolation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("filter_field", ["subject_ids", "class_ids"])
def test_subject_and_class_id_filters_restrict_returned_sessions(
    auth_client: Client,
    project: Project,
    project_db: Session,
    filter_field: str,
    index: int,
) -> None:
    # Three sessions, each with its own (class, subject) pair in the same week.
    # Filtering by a single subject id or class id must return only its session.
    year = make_year(project_db)
    classes = [make_class(project_db, year=year) for _ in range(3)]
    subjects = [make_subject(project_db, year=year) for _ in range(3)]
    sessions = []
    for class_row, subject in zip(classes, subjects, strict=True):
        session_row = make_session(project_db)
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
        )
        sessions.append(session_row)

    target_id = subjects[index].id if filter_field == "subject_ids" else classes[index].id
    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&{filter_field}={target_id}"),
    )

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    returned = blocks[0]["sessions"]
    assert len(returned) == 1
    assert returned[0]["id"] == str(sessions[index].id)
    # The other two sessions are excluded.
    other_ids = {str(s.id) for i, s in enumerate(sessions) if i != index}
    assert {s["id"] for s in returned}.isdisjoint(other_ids)


def test_only_requested_years_sessions_are_returned(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Year A and year B live in the same project; requesting year A must never
    # surface year B's session (Class.year_id is the isolation boundary).
    degree = make_degree(project_db)
    year_a = make_year(project_db, degree=degree, number=1)
    year_b = make_year(project_db, degree=degree, number=2)

    class_a = make_class(project_db, year=year_a)
    subject_a = make_subject(project_db, year=year_a)
    session_a = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a,
        subject=subject_a,
    )

    class_b = make_class(project_db, year=year_b)
    subject_b = make_subject(project_db, year=year_b)
    session_b = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b,
        subject=subject_b,
    )

    response = auth_client.get(_sessions_url(project.pk, f"?year_id={year_a.id}"))

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    returned_ids = {s["id"] for block in blocks for s in block["sessions"]}
    assert str(session_a.id) in returned_ids
    assert str(session_b.id) not in returned_ids


# ---------------------------------------------------------------------------
# -- Out-of-domain query values & wrong methods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_param",
    [
        "weekdays=funday",
        "subject_ids=not-a-uuid",
        "class_ids=not-a-uuid",
    ],
)
def test_invalid_weekday_and_invalid_list_uuids_return_400(
    auth_client: Client,
    project: Project,
    project_db: Session,
    bad_param: str,
) -> None:
    # Garbage in the enum / list[UUID] query fields is rejected before any DB
    # work; a well-formed (but unused) year_id keeps the failure isolated.
    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={uuid.uuid7()}&{bad_param}"),
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


@pytest.mark.parametrize(
    "bad_weekday",
    ["funday", "sunday", "lunes", "13", ""],
)
def test_invalid_weekday_value_returns_400(
    auth_client: Client,
    project: Project,
    project_db: Session,
    bad_weekday: str,
) -> None:
    # WeekDay is a StrEnum (mon..sat, plus PT aliases); anything else is
    # rejected as generic.invalid_body rather than silently dropped.
    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={uuid.uuid7()}&weekdays={bad_weekday}"),
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


@pytest.mark.parametrize("day", list(WeekDay))
def test_each_weekday_filter_is_honored(
    auth_client: Client,
    project: Project,
    project_db: Session,
    day: WeekDay,
) -> None:
    # Seed one session on every weekday; filtering to a single day returns
    # exactly that day's session, exhaustively over the whole WeekDay enum.
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    sessions_by_day = {}
    for weekday in WeekDay:
        session_row = make_session(project_db, weekday=weekday)
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )
        sessions_by_day[weekday] = session_row

    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&weekdays={day.value}"),
    )

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    returned = blocks[0]["sessions"]
    assert len(returned) == 1
    assert returned[0]["id"] == str(sessions_by_day[day].id)
    assert returned[0]["weekday"] == day.value


def test_multiple_weekdays_query_honors_every_value(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Repeated ?weekdays=monday&weekdays=tuesday exercises the list-flatten
    # branch (>1 element) and both days must be honored, wednesday excluded.
    year = make_year(project_db)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    by_day = {}
    for weekday in (WeekDay.MONDAY, WeekDay.TUESDAY, WeekDay.WEDNESDAY):
        session_row = make_session(project_db, weekday=weekday)
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )
        by_day[weekday] = session_row

    response = auth_client.get(
        _sessions_url(project.pk, f"?year_id={year.id}&weekdays=monday&weekdays=tuesday"),
    )

    assert response.status_code == 200
    blocks = response.json()["data"]["blocks"]
    assert len(blocks) == 1
    returned = blocks[0]["sessions"]
    assert {s["id"] for s in returned} == {
        str(by_day[WeekDay.MONDAY].id),
        str(by_day[WeekDay.TUESDAY].id),
    }
    assert {s["weekday"] for s in returned} == {"monday", "tuesday"}
    assert str(by_day[WeekDay.WEDNESDAY].id) not in {s["id"] for s in returned}


@pytest.mark.parametrize("path", ["sessions", "stats"])
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_non_get_methods_on_sessions_and_stats_return_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    path: str,
    method: str,
) -> None:
    # Both views expose only get(); Django refuses any other verb with 405
    # (the auth/project decorators wrap get, so a non-GET never reaches them).
    url = _sessions_url(project.pk) if path == "sessions" else _stats_url(project.pk)
    response = getattr(auth_client, method)(url)
    assert response.status_code == 405
