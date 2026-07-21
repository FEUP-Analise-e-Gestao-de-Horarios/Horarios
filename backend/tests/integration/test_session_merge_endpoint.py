"""Integration tests for the session merge endpoint (reverse of split).

``POST /api/projects/<pk>/sessions/<sid>/merge/`` — recombines a session's
classes into another matching session, deleting the source. Two sessions
only merge when they already match on weekday/time/duration/type/teachers/
rooms/subject; merge doesn't reconcile any of those, it only recombines
classes.
"""

import datetime
import json
import uuid

from django.test import Client

from src.projects.models import Project
from src.projects.projects_db.dao.session_class_subject_dao import SessionClassSubjectDAO
from src.projects.projects_db.models import Session as SessionModel
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
    return f"/api/projects/{project_id}/sessions/{session_id}/merge/"


def _post(client: Client, url: str, body: dict) -> object:
    return client.post(url, data=json.dumps(body), content_type="application/json")


def _seed_matching_pair(project_db, **overrides):
    """Two sessions that already match on everything but their classes."""
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    teacher = make_teacher(project_db)
    room = make_room(project_db)

    session_kwargs = {
        "weekday": WeekDay.MONDAY,
        "start_time": 900,
        "duration": 2,
        "type": "T",
        **overrides,
    }
    source = make_session(project_db, **session_kwargs)
    target = make_session(project_db, **session_kwargs)
    for session_row, klass in ((source, class_a), (target, class_b)):
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
        )
        link_session_teacher(project_db, session_row=session_row, teacher=teacher)
        link_session_room(project_db, session_row=session_row, room=room)

    return source, target, class_a, class_b, subject, year


# ---------------------------------------------------------------------------
# -- Auth / existence
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project: Project, project_db) -> None:
    source, target, *_ = _seed_matching_pair(project_db)
    response = _post(Client(), _url(project.pk, source.id), {"target_session_id": str(target.id)})
    assert response.status_code == 401


def test_unknown_source_session_returns_404(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    _source, target, *_ = _seed_matching_pair(project_db)
    response = _post(
        auth_client,
        _url(project.pk, uuid.uuid7()),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.sessions.not_found"


def test_unknown_target_session_returns_404(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    source, _target, *_ = _seed_matching_pair(project_db)
    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(uuid.uuid7())},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "projects.sessions.not_found"


def test_merging_with_self_returns_400(auth_client: Client, project: Project, project_db) -> None:
    source, _target, *_ = _seed_matching_pair(project_db)
    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(source.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


# ---------------------------------------------------------------------------
# -- Happy path
# ---------------------------------------------------------------------------


def test_merges_classes_and_deletes_source(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    source, target, class_a, class_b, subject, _year = _seed_matching_pair(project_db)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(target.id)
    assert {c["id"] for c in data["classes"]} == {str(class_a.id), str(class_b.id)}
    assert {s["id"] for s in data["subjects"]} == {str(subject.id)}

    db_session = get_session(general_db(project.pk))
    try:
        assert db_session.get(SessionModel, source.id) is None
    finally:
        db_session.close()


# ---------------------------------------------------------------------------
# -- Compatibility validation
# ---------------------------------------------------------------------------


def test_mismatched_start_time_returns_400(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    source = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    target = make_session(project_db, weekday=WeekDay.MONDAY, start_time=1030, duration=2)
    make_session_class_subject(project_db, session_row=source, class_row=class_a, subject=subject)
    make_session_class_subject(project_db, session_row=target, class_row=class_b, subject=subject)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_mismatched_teachers_returns_400(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    source, target, *_ = _seed_matching_pair(project_db)
    extra_teacher = make_teacher(project_db, acronym="EXT")
    link_session_teacher(project_db, session_row=target, teacher=extra_teacher)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_mismatched_rooms_returns_400(auth_client: Client, project: Project, project_db) -> None:
    source, target, *_ = _seed_matching_pair(project_db)
    extra_room = make_room(project_db, name="Extra Room")
    link_session_room(project_db, session_row=target, room=extra_room)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_mismatched_subject_returns_400(auth_client: Client, project: Project, project_db) -> None:
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject_a = make_subject(project_db, year=year, acronym="AAA")
    subject_b = make_subject(project_db, year=year, acronym="BBB")
    source = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    target = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    make_session_class_subject(project_db, session_row=source, class_row=class_a, subject=subject_a)
    make_session_class_subject(project_db, session_row=target, class_row=class_b, subject=subject_b)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_overlapping_classes_returns_400(auth_client: Client, project: Project, project_db) -> None:
    year = make_year(project_db)
    shared_class = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    source = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    target = make_session(project_db, weekday=WeekDay.MONDAY, start_time=900, duration=2)
    make_session_class_subject(
        project_db,
        session_row=source,
        class_row=shared_class,
        subject=subject,
    )
    make_session_class_subject(
        project_db,
        session_row=target,
        class_row=shared_class,
        subject=subject,
    )

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {"target_session_id": str(target.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


# ---------------------------------------------------------------------------
# -- weeks fan-out
# ---------------------------------------------------------------------------


def test_weeks_scope_only_merges_matching_weeks(
    auth_client: Client,
    project: Project,
    project_db,
) -> None:
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    teacher = make_teacher(project_db)

    source_block = uuid.uuid7()
    target_block = uuid.uuid7()
    week_a = datetime.date(2025, 9, 15)
    week_b = datetime.date(2025, 9, 22)

    source_a = make_session(
        project_db,
        week=week_a,
        original_block_id=source_block,
        weekday=WeekDay.MONDAY,
        start_time=900,
        duration=2,
    )
    source_b = make_session(
        project_db,
        week=week_b,
        original_block_id=source_block,
        weekday=WeekDay.MONDAY,
        start_time=900,
        duration=2,
    )
    # Target only exists in week_a — week_b's source row has nothing to merge into.
    target_a = make_session(
        project_db,
        week=week_a,
        original_block_id=target_block,
        weekday=WeekDay.MONDAY,
        start_time=900,
        duration=2,
    )

    for row in (source_a, source_b):
        make_session_class_subject(project_db, session_row=row, class_row=class_a, subject=subject)
        link_session_teacher(project_db, session_row=row, teacher=teacher)
    make_session_class_subject(project_db, session_row=target_a, class_row=class_b, subject=subject)
    link_session_teacher(project_db, session_row=target_a, teacher=teacher)

    response = _post(
        auth_client,
        _url(project.pk, source_a.id),
        {
            "target_session_id": str(target_a.id),
            "weeks": ["2025-09-15", "2025-09-22"],
        },
    )
    assert response.status_code == 200

    db_session = get_session(general_db(project.pk))
    try:
        assert db_session.get(SessionModel, source_a.id) is None
        # week_b's source row is untouched — target never had a week_b row.
        untouched = db_session.get(SessionModel, source_b.id)
        assert untouched is not None
        scs_dao = SessionClassSubjectDAO(db_session)
        assert {link.class_id for link in scs_dao.get_by_session(source_b.id)} == {class_a.id}
        assert {link.class_id for link in scs_dao.get_by_session(target_a.id)} == {
            class_a.id,
            class_b.id,
        }
    finally:
        db_session.close()


def test_no_matching_weeks_returns_400(auth_client: Client, project: Project, project_db) -> None:
    year = make_year(project_db)
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    source = make_session(project_db, week=datetime.date(2025, 9, 15), weekday=WeekDay.MONDAY)
    target = make_session(project_db, week=datetime.date(2025, 9, 22), weekday=WeekDay.MONDAY)
    make_session_class_subject(project_db, session_row=source, class_row=class_a, subject=subject)
    make_session_class_subject(project_db, session_row=target, class_row=class_b, subject=subject)

    response = _post(
        auth_client,
        _url(project.pk, source.id),
        {
            "target_session_id": str(target.id),
            "weeks": ["2025-09-15", "2025-09-22"],
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
