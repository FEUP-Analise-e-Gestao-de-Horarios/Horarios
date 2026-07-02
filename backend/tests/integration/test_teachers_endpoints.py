"""Integration tests for the project *teachers* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/teachers/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/teachers/<teacher_id>`` — the detail view (subjects,
  classes, week blocks and red blocks), including the 404 for an unknown
  teacher id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``TeacherDAO`` + the response schemas. Order-independent facts are compared
via lookup dicts; the volatile ``timestamp`` is only checked for presence.
"""

import uuid

from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    link_session_teacher,
    make_class,
    make_session,
    make_session_class_subject,
    make_subject,
    make_teacher,
    make_teacher_red_block,
    make_year,
)


def _list_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/teachers/"


def _detail_url(project_id: int, teacher_id) -> str:
    return f"/api/projects/{project_id}/teachers/{teacher_id}"


# ---------------------------------------------------------------------------
# -- Auth / project decorators
# ---------------------------------------------------------------------------


def test_list_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_list_url(project.pk))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_list_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_list_url(project.pk + 1000))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_detail_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# -- List
# ---------------------------------------------------------------------------


def test_list_empty_db(auth_client: Client, project: Project, project_db: Session) -> None:
    response = auth_client.get(_list_url(project.pk))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["teachers"] == []
    assert data["count"] == 0


def test_list_reports_subject_class_session_and_red_block_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A teacher wired to one session (which carries a class + subject) and one
    # red block, so every count is 1.
    klass = make_class(project_db, code="1LEIC01")
    subject = make_subject(project_db, year=klass.year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    teacher = make_teacher(project_db, acronym="AAA", name="Alpha", number=100)
    link_session_teacher(project_db, session_row=session_row, teacher=teacher)
    make_teacher_red_block(project_db, teacher=teacher, hour=1000)

    # A second teacher with nothing attached, to check the 0 counts.
    make_teacher(project_db, acronym="BBB", name="Beta", number=200)

    response = auth_client.get(_list_url(project.pk))

    data = response.json()["data"]
    assert data["count"] == 2
    by_acronym = {t["acronym"]: t for t in data["teachers"]}
    assert by_acronym["AAA"]["subjects"] == 1
    assert by_acronym["AAA"]["classes"] == 1
    assert by_acronym["AAA"]["sessions"] == 1
    assert by_acronym["AAA"]["red_blocks"] == 1
    assert by_acronym["AAA"]["number"] == 100
    assert by_acronym["AAA"]["id"] == str(teacher.id)
    assert by_acronym["BBB"]["subjects"] == 0
    assert by_acronym["BBB"]["classes"] == 0
    assert by_acronym["BBB"]["sessions"] == 0
    assert by_acronym["BBB"]["red_blocks"] == 0


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_teacher_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.teachers.not_found"


def test_detail_returns_subjects_classes_blocks_and_red_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    teacher = make_teacher(project_db, acronym="XYZ", name="Xavier Yin Zulu", number=500)
    klass = make_class(project_db, code="1LEIC01")
    subject = make_subject(
        project_db,
        year=klass.year,
        number=7,
        code="UC777",
        acronym="PRG",
        name="Programming",
    )
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    link_session_teacher(project_db, session_row=session_row, teacher=teacher)
    make_teacher_red_block(project_db, teacher=teacher, hour=1400, weekday=WeekDay.TUESDAY)

    response = auth_client.get(_detail_url(project.pk, teacher.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(teacher.id)
    assert data["number"] == 500
    assert data["acronym"] == "XYZ"
    assert data["name"] == "Xavier Yin Zulu"

    # Subjects taught by the teacher.
    assert [s["id"] for s in data["subjects"]] == [str(subject.id)]
    assert data["subjects"][0]["number"] == 7
    assert data["subjects"][0]["code"] == "UC777"
    assert data["subjects"][0]["acronym"] == "PRG"
    assert data["subjects"][0]["name"] == "Programming"

    # Classes taught by the teacher.
    assert [c["id"] for c in data["classes"]] == [str(klass.id)]
    assert data["classes"][0]["code"] == "1LEIC01"
    assert data["classes"][0]["year_id"] == str(klass.year_id)

    # One week block carrying the single seeded session.
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert len(block["sessions"]) == 1
    block_session = block["sessions"][0]
    assert [t["id"] for t in block_session["teachers"]] == [str(teacher.id)]
    assert block_session["subjects"][0]["code"] == "UC777"
    assert block_session["classes"][0]["code"] == "1LEIC01"

    # One red block.
    assert len(data["red_blocks"]) == 1
    red_block = data["red_blocks"][0]
    assert red_block["hour"] == 1400
    assert red_block["weekday"] == "tuesday"


def test_detail_excludes_other_teachers_data(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A single shared year/degree so the two classes below do not both
    # auto-create a degree with the same (unique) acronym.
    year = make_year(project_db)

    # Teacher A: own session carrying its own class + subject, plus its own red block.
    teacher_a = make_teacher(project_db, acronym="AAA", name="Alpha", number=100)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    subject_a = make_subject(project_db, year=year, acronym="SA", name="Subject A")
    session_a = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a,
        subject=subject_a,
    )
    link_session_teacher(project_db, session_row=session_a, teacher=teacher_a)
    make_teacher_red_block(project_db, teacher=teacher_a, hour=1000, weekday=WeekDay.MONDAY)

    # Teacher B: a completely distinct session/class/subject and its own red block.
    teacher_b = make_teacher(project_db, acronym="BBB", name="Beta", number=200)
    class_b = make_class(project_db, year=year, code="2LEIC02")
    subject_b = make_subject(project_db, year=year, acronym="SB", name="Subject B")
    session_b = make_session(project_db, start_time=14, weekday=WeekDay.FRIDAY)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b,
        subject=subject_b,
    )
    link_session_teacher(project_db, session_row=session_b, teacher=teacher_b)
    make_teacher_red_block(project_db, teacher=teacher_b, hour=1600, weekday=WeekDay.FRIDAY)

    response = auth_client.get(_detail_url(project.pk, teacher_a.id))

    assert response.status_code == 200
    data = response.json()["data"]

    # Only A's subject/class/red block are present; none of B's leak in.
    assert {s["id"] for s in data["subjects"]} == {str(subject_a.id)}
    assert {c["id"] for c in data["classes"]} == {str(class_a.id)}
    assert str(subject_b.id) not in {s["id"] for s in data["subjects"]}
    assert str(class_b.id) not in {c["id"] for c in data["classes"]}

    # Only A's session appears in the week blocks.
    session_ids = {s["id"] for block in data["blocks"] for s in block["sessions"]}
    assert session_ids == {str(session_a.id)}
    assert str(session_b.id) not in session_ids

    # Only A's red block (hour 1000, monday); B's (1600, friday) is excluded.
    assert [(rb["hour"], rb["weekday"]) for rb in data["red_blocks"]] == [(1000, "monday")]


# ---------------------------------------------------------------------------
# -- List stats: distinct / coalesce branches
# ---------------------------------------------------------------------------


def test_list_counts_distinct_subjects_and_classes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # One teacher wired to two sessions. Both sessions teach the SAME subject but
    # cover two different classes, and one class is repeated across the sessions.
    # Without .distinct() the join fans out: subjects would count 3 and classes 3.
    teacher = make_teacher(project_db, acronym="AAA", name="Alpha", number=100)
    subject = make_subject(project_db, acronym="ONE", name="Only Subject")
    year = subject.years[0]
    class_1 = make_class(project_db, year=year, code="C1")
    class_2 = make_class(project_db, year=year, code="C2")

    session_1 = make_session(project_db, start_time=9)
    make_session_class_subject(
        project_db,
        session_row=session_1,
        class_row=class_1,
        subject=subject,
    )
    link_session_teacher(project_db, session_row=session_1, teacher=teacher)

    session_2 = make_session(project_db, start_time=11)
    # session_2 repeats class_1 (same subject) AND introduces class_2.
    make_session_class_subject(
        project_db,
        session_row=session_2,
        class_row=class_1,
        subject=subject,
    )
    make_session_class_subject(
        project_db,
        session_row=session_2,
        class_row=class_2,
        subject=subject,
    )
    link_session_teacher(project_db, session_row=session_2, teacher=teacher)

    response = auth_client.get(_list_url(project.pk))

    data = response.json()["data"]
    assert data["count"] == 1
    stats = data["teachers"][0]
    assert stats["id"] == str(teacher.id)
    assert stats["subjects"] == 1  # distinct subject
    assert stats["classes"] == 2  # distinct classes C1, C2 (C1 repeated)
    assert stats["sessions"] == 2  # distinct sessions


def test_list_teacher_session_without_class_subject_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Teacher linked to a session that has NO SessionClassSubject row: the
    # outerjoin leaves subject_id/class_id NULL, so count(distinct) coalesces to
    # 0 while the session itself is still counted once.
    teacher = make_teacher(project_db, acronym="AAA", name="Alpha", number=100)
    session_row = make_session(project_db)
    link_session_teacher(project_db, session_row=session_row, teacher=teacher)

    response = auth_client.get(_list_url(project.pk))

    data = response.json()["data"]
    assert data["count"] == 1
    stats = data["teachers"][0]
    assert stats["id"] == str(teacher.id)
    assert stats["sessions"] == 1
    assert stats["subjects"] == 0
    assert stats["classes"] == 0
    assert stats["red_blocks"] == 0


def test_detail_malformed_id_returns_404_and_401_body_checked(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # (1) A non-UUID path segment never matches the <uuid:teacher_id> converter,
    # so it is a resolver 404 rather than the projects.teachers.not_found envelope.
    response = auth_client.get(f"/api/projects/{project.pk}/teachers/not-a-uuid")
    assert response.status_code == 404
    assert b"projects.teachers.not_found" not in response.content

    # (2) Detail without auth returns the standard auth envelope, not just a 401.
    response = Client().get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
