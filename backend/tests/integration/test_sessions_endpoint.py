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

import uuid

from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    make_class,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)


def _sessions_url(project_id: int, query: str = "") -> str:
    return f"/api/projects/{project_id}/sessions/{query}"


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
