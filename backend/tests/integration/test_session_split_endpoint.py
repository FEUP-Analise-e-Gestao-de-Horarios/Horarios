"""Integration tests for the session split endpoint.

``POST /api/projects/<pk>/sessions/<sid>/split/`` — detaches some of a
session's classes into a brand new session, so a shared multi-class lecture
can send one class off to a different time/teacher/room without touching the
classes staying behind.
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
    return f"/api/projects/{project_id}/sessions/{session_id}/split/"


def _post(client: Client, url: str, body: dict) -> object:
    return client.post(url, data=json.dumps(body), content_type="application/json")


def _seed_three_class_session(project_db):
    year = make_year(project_db)
    classes = [make_class(project_db, year=year, code=f"1LEIC0{i}") for i in (1, 2, 3)]
    subject = make_subject(project_db, year=year)
    session_row = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    for klass in classes:
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )
    return session_row, classes, subject, year


# ---------------------------------------------------------------------------
# -- Auth / existence
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project: Project, project_db) -> None:
    session_row, classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        Client(),
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "weekday": "wednesday",
            "start_time": 1000,
            "duration": 2,
        },
    )
    assert response.status_code == 401


def test_unknown_session_returns_404(auth_client: Client, project: Project, project_db) -> None:
    response = _post(
        auth_client,
        _url(project.pk, uuid.uuid7()),
        {"class_ids": [str(uuid.uuid7())], "weekday": "monday", "start_time": 900, "duration": 2},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.sessions.not_found"


# ---------------------------------------------------------------------------
# -- Core split behavior
# ---------------------------------------------------------------------------


def test_splits_one_class_off_leaving_the_others_on_the_original(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, classes, subject, _year = _seed_three_class_session(project_db)
    middle = classes[1]  # detaching the middle class is what breaks contiguity

    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(middle.id)],
            "weekday": "wednesday",
            "start_time": 1400,
            "duration": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]

    original = data["original"]
    assert original["id"] == str(session_row.id)
    # The other two classes are untouched — still on the original session,
    # at its original day/time. This is what lets the schedule grid draw the
    # two remaining pieces as one session with a gap (connected by an arc)
    # instead of losing them.
    assert {c["id"] for c in original["classes"]} == {str(classes[0].id), str(classes[2].id)}
    assert original["weekday"] == "monday"
    assert original["start_time"] == 900

    created = data["created"]
    assert created["id"] != str(session_row.id)
    assert {c["id"] for c in created["classes"]} == {str(middle.id)}
    assert created["weekday"] == "wednesday"
    assert created["start_time"] == 1400
    assert created["duration"] == 3
    assert {s["id"] for s in created["subjects"]} == {str(subject.id)}
    # A fresh recurring block of its own, not reusing the original's.
    assert created["original_block_id"] != original["original_block_id"]


def test_created_session_inherits_teachers_and_rooms_when_omitted(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, classes, _, _year = _seed_three_class_session(project_db)
    teacher = make_teacher(project_db)
    room = make_room(project_db)
    link_session_teacher(project_db, session_row=session_row, teacher=teacher)
    link_session_room(project_db, session_row=session_row, room=room)

    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "weekday": "tuesday",
            "start_time": 1100,
            "duration": 2,
        },
    )

    assert response.status_code == 200
    created = response.json()["data"]["created"]
    assert {t["id"] for t in created["teachers"]} == {str(teacher.id)}
    assert {r["id"] for r in created["rooms"]} == {str(room.id)}
    # Untouched on the original.
    original = response.json()["data"]["original"]
    assert {t["id"] for t in original["teachers"]} == {str(teacher.id)}
    assert {r["id"] for r in original["rooms"]} == {str(room.id)}


def test_explicit_subject_ids_used_for_created_session(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, classes, _, year = _seed_three_class_session(project_db)
    other_subject = make_subject(project_db, year=year, acronym="OTH")

    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "weekday": "friday",
            "start_time": 1600,
            "duration": 1,
            "subject_ids": [str(other_subject.id)],
        },
    )

    assert response.status_code == 200
    created = response.json()["data"]["created"]
    assert {s["id"] for s in created["subjects"]} == {str(other_subject.id)}


def test_new_class_ids_reassigns_the_detached_slot_to_a_different_class(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    # classes[0] is detached off the shared session, but the resulting new
    # session should teach a class that was never even part of it — the
    # "move this turma's slot to a different turma entirely" case.
    session_row, classes, _, year = _seed_three_class_session(project_db)
    unrelated_class = make_class(project_db, year=year, code="2LEIC01")

    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "new_class_ids": [str(unrelated_class.id)],
            "weekday": "friday",
            "start_time": 1600,
            "duration": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    # classes[0] left the original (same as a plain split)...
    assert {c["id"] for c in data["original"]["classes"]} == {
        str(classes[1].id),
        str(classes[2].id),
    }
    # ...but the new session teaches unrelated_class, not classes[0].
    assert {c["id"] for c in data["created"]["classes"]} == {str(unrelated_class.id)}


def test_unknown_new_class_id_returns_404(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "new_class_ids": [str(uuid.uuid7())],
            "weekday": "monday",
            "start_time": 900,
            "duration": 2,
        },
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.classes.not_found"


# ---------------------------------------------------------------------------
# -- Validation
# ---------------------------------------------------------------------------


def test_class_not_on_session_returns_404(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, _classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(uuid.uuid7())],
            "weekday": "monday",
            "start_time": 900,
            "duration": 2,
        },
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.classes.not_found"


def test_splitting_every_class_off_returns_400(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    session_row, classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(c.id) for c in classes],
            "weekday": "monday",
            "start_time": 900,
            "duration": 2,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_empty_class_ids_returns_400(auth_client: Client, project: Project, project_db) -> None:
    session_row, _classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {"class_ids": [], "weekday": "monday", "start_time": 900, "duration": 2},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_unknown_teacher_id_returns_404(auth_client: Client, project: Project, project_db) -> None:
    session_row, classes, _, _year = _seed_three_class_session(project_db)
    response = _post(
        auth_client,
        _url(project.pk, session_row.id),
        {
            "class_ids": [str(classes[0].id)],
            "weekday": "monday",
            "start_time": 900,
            "duration": 2,
            "teacher_ids": [str(uuid.uuid7())],
        },
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.teachers.not_found"


# ---------------------------------------------------------------------------
# -- weeks fan-out
# ---------------------------------------------------------------------------


def test_weeks_fans_split_out_to_siblings(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    classes = [make_class(project_db, year=year, code=f"1LEIC0{i}") for i in (1, 2)]
    subject = make_subject(project_db, year=year)
    block_id = uuid.uuid7()
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)
    session_a = make_session(
        project_db,
        week=week_a,
        original_block_id=block_id,
        weekday=WeekDay.MONDAY,
    )
    session_b = make_session(
        project_db,
        week=week_b,
        original_block_id=block_id,
        weekday=WeekDay.MONDAY,
    )
    for row in (session_a, session_b):
        for klass in classes:
            make_session_class_subject(
                project_db,
                session_row=row,
                class_row=klass,
                subject=subject,
            )

    response = _post(
        auth_client,
        _url(project.pk, session_a.id),
        {
            "class_ids": [str(classes[0].id)],
            "weekday": "thursday",
            "start_time": 1200,
            "duration": 2,
            "weeks": ["2025-09-15", "2025-09-22"],
        },
    )
    assert response.status_code == 200

    db_session = get_session(general_db(project.pk))
    try:
        scs_dao = SessionClassSubjectDAO(db_session)
        # session_a and session_b both lost classes[0].
        assert {link.class_id for link in scs_dao.get_by_session(session_a.id)} == {classes[1].id}
        assert {link.class_id for link in scs_dao.get_by_session(session_b.id)} == {classes[1].id}
    finally:
        db_session.close()
