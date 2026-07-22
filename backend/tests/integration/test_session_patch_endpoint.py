"""Integration tests for the session PATCH endpoint (contract C1).

``PATCH /api/projects/<pk>/sessions/<sid>/`` — partial update of a single
session's weekday/start_time/duration/teachers/rooms/classes/subject, with an
optional ``weeks`` fan-out to every sibling sharing the target's
``original_block_id``.
"""

import datetime
import json
import uuid

from django.test import Client

from src.projects.models import Project
from src.projects.projects_db.dao.session_class_subject_dao import SessionClassSubjectDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    link_session_room,
    link_session_teacher,
    make_class,
    make_room,
    make_session,
    make_session_class_subject,
    make_subject,
    make_teacher,
    make_year,
)


def _url(project_id: int, session_id: object) -> str:
    return f"/api/projects/{project_id}/sessions/{session_id}/"


def _patch(client: Client, url: str, body: dict) -> object:
    return client.patch(url, data=json.dumps(body), content_type="application/json")


# ---------------------------------------------------------------------------
# -- Auth / project / session existence
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(Client(), _url(project.pk, session_row.id), {"duration": 3})
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = _patch(auth_client, _url(project.pk + 1000, uuid.uuid7()), {"duration": 3})
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_unknown_session_returns_404(auth_client: Client, project: Project, project_db) -> None:
    response = _patch(auth_client, _url(project.pk, uuid.uuid7()), {"duration": 3})
    assert response.status_code == 404
    assert response.json()["error"] == "projects.sessions.not_found"


def test_non_owner_can_still_patch(other_auth_client: Client, project: Project, project_db) -> None:
    # require_project only checks existence — matches every other endpoint's
    # access model, not a stricter rule invented for this one.
    session_row = make_session(project_db, duration=2)
    response = _patch(other_auth_client, _url(project.pk, session_row.id), {"duration": 4})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# -- Plain field updates
# ---------------------------------------------------------------------------


def test_patches_weekday_start_time_duration(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row = make_session(
        project_db,
        weekday=WeekDay.MONDAY,
        start_time=900,
        duration=2,
    )

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"weekday": "wednesday", "start_time": 1030, "duration": 3},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["weekday"] == "wednesday"
    assert data["start_time"] == 1030
    assert data["duration"] == 3


def test_omitted_fields_are_left_unchanged(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row = make_session(project_db, weekday=WeekDay.TUESDAY, start_time=900, duration=2)

    response = _patch(auth_client, _url(project.pk, session_row.id), {"duration": 4})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["weekday"] == "tuesday"
    assert data["start_time"] == 900
    assert data["duration"] == 4


def test_invalid_duration_returns_400(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(auth_client, _url(project.pk, session_row.id), {"duration": 0})
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


# ---------------------------------------------------------------------------
# -- Teachers / rooms (wholesale replace)
# ---------------------------------------------------------------------------


def test_replaces_teachers_wholesale(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    old_teacher = make_teacher(project_db, acronym="OLD")
    link_session_teacher(project_db, session_row=session_row, teacher=old_teacher)
    new_teacher = make_teacher(project_db, acronym="NEW")

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"teacher_ids": [str(new_teacher.id)]},
    )

    assert response.status_code == 200
    teacher_ids = {t["id"] for t in response.json()["data"]["teachers"]}
    assert teacher_ids == {str(new_teacher.id)}


def test_unknown_teacher_id_returns_404(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"teacher_ids": [str(uuid.uuid7())]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.teachers.not_found"


def test_replaces_rooms_wholesale(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    old_room = make_room(project_db, name="Old Room")
    link_session_room(project_db, session_row=session_row, room=old_room)
    new_room = make_room(project_db, name="New Room")

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"room_ids": [str(new_room.id)]},
    )

    assert response.status_code == 200
    room_ids = {r["id"] for r in response.json()["data"]["rooms"]}
    assert room_ids == {str(new_room.id)}


def test_unknown_room_id_returns_404(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"room_ids": [str(uuid.uuid7())]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.rooms.not_found"


# ---------------------------------------------------------------------------
# -- Classes / subject (junction rebuild)
# ---------------------------------------------------------------------------


def test_patches_classes_and_subject_together(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    old_class = make_class(project_db, year=year, code="1LEIC01")
    old_subject = make_subject(project_db, year=year, acronym="OLD")
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=old_class,
        subject=old_subject,
    )
    new_class = make_class(project_db, year=year, code="1LEIC02")
    new_subject = make_subject(project_db, year=year, acronym="NEW")

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"class_ids": [str(new_class.id)], "subject_ids": [str(new_subject.id)]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert {c["id"] for c in data["classes"]} == {str(new_class.id)}
    assert {s["id"] for s in data["subjects"]} == {str(new_subject.id)}


def test_class_ids_without_subject_ids_keeps_existing_subject(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    old_class = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=old_class,
        subject=subject,
    )
    new_class = make_class(project_db, year=year, code="1LEIC02")

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"class_ids": [str(new_class.id)]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert {c["id"] for c in data["classes"]} == {str(new_class.id)}
    assert {s["id"] for s in data["subjects"]} == {str(subject.id)}


def test_class_ids_with_ambiguous_existing_subjects_requires_explicit_subject_ids(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject_a = make_subject(project_db, year=year, acronym="AAA")
    subject_b = make_subject(project_db, year=year, acronym="BBB")
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class_a,
        subject=subject_a,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class_b,
        subject=subject_b,
    )
    new_class = make_class(project_db, year=year, code="1LEIC03")

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"class_ids": [str(new_class.id)]},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_empty_class_ids_clears_classes_and_subjects(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    klass = make_class(project_db, year=year)
    subject = make_subject(project_db, year=year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = _patch(auth_client, _url(project.pk, session_row.id), {"class_ids": []})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["classes"] == []
    assert data["subjects"] == []


def test_multiple_subject_ids_returns_400(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    subject_a = make_subject(project_db, year=year, acronym="AAA")
    subject_b = make_subject(project_db, year=year, acronym="BBB")
    session_row = make_session(project_db)

    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"subject_ids": [str(subject_a.id), str(subject_b.id)]},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_unknown_class_id_returns_404(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"class_ids": [str(uuid.uuid7())]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.classes.not_found"


def test_unknown_subject_id_returns_404(auth_client: Client, project: Project, project_db) -> None:
    session_row = make_session(project_db)
    response = _patch(
        auth_client,
        _url(project.pk, session_row.id),
        {"subject_ids": [str(uuid.uuid7())]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.subjects.not_found"


# ---------------------------------------------------------------------------
# -- weeks fan-out (siblings sharing original_block_id)
# ---------------------------------------------------------------------------


def test_weeks_fans_out_to_siblings_sharing_original_block_id(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    block_id = uuid.uuid7()
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)
    week_c = datetime.date(2025, 9, 29)
    session_a = make_session(project_db, week=week_a, original_block_id=block_id, start_time=900)
    session_b = make_session(project_db, week=week_b, original_block_id=block_id, start_time=900)
    session_c = make_session(project_db, week=week_c, original_block_id=block_id, start_time=900)

    response = _patch(
        auth_client,
        _url(project.pk, session_a.id),
        {"start_time": 1400, "weeks": ["2025-09-15", "2025-09-22"]},
    )
    assert response.status_code == 200

    db_session = get_session(general_db(project.pk))
    try:
        db_session.expire_all()
        assert db_session.get(type(session_a), session_a.id).start_time == 1400
        assert db_session.get(type(session_b), session_b.id).start_time == 1400
        # Not in the weeks list: untouched.
        assert db_session.get(type(session_c), session_c.id).start_time == 900
    finally:
        db_session.close()


def test_omitted_weeks_only_patches_the_target_session(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    block_id = uuid.uuid7()
    session_a = make_session(
        project_db,
        week=datetime.date(2025, 9, 15),
        original_block_id=block_id,
        start_time=900,
    )
    session_b = make_session(
        project_db,
        week=datetime.date(2025, 9, 22),
        original_block_id=block_id,
        start_time=900,
    )

    response = _patch(auth_client, _url(project.pk, session_a.id), {"start_time": 1400})
    assert response.status_code == 200

    db_session = get_session(general_db(project.pk))
    try:
        db_session.expire_all()
        assert db_session.get(type(session_a), session_a.id).start_time == 1400
        assert db_session.get(type(session_b), session_b.id).start_time == 900
    finally:
        db_session.close()


def test_weeks_fan_out_also_rebuilds_sibling_classes(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    old_class = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    new_class = make_class(project_db, year=year, code="1LEIC02")

    block_id = uuid.uuid7()
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)
    session_a = make_session(project_db, week=week_a, original_block_id=block_id)
    session_b = make_session(project_db, week=week_b, original_block_id=block_id)
    for row in (session_a, session_b):
        make_session_class_subject(
            project_db,
            session_row=row,
            class_row=old_class,
            subject=subject,
        )

    response = _patch(
        auth_client,
        _url(project.pk, session_a.id),
        {"class_ids": [str(new_class.id)], "weeks": ["2025-09-15", "2025-09-22"]},
    )
    assert response.status_code == 200

    db_session = get_session(general_db(project.pk))
    try:
        sibling_classes = {
            scs.class_id for scs in SessionClassSubjectDAO(db_session).get_by_session(session_b.id)
        }
        assert sibling_classes == {new_class.id}
    finally:
        db_session.close()
