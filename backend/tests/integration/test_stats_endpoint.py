"""Integration tests for the project *stats* endpoint.

The single route is covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/stats`` — the project overview counts view (note the
  absence of a trailing slash).

Assertions target the ``SuccessResponse`` envelope and the ``StatsResponse``
wire shape: total counts of every top-level entity across the project DB. The
volatile ``timestamp`` is only checked for presence.
"""

from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from tests.factories import (
    make_class,
    make_degree,
    make_room,
    make_session,
    make_session_class_subject,
    make_subject,
    make_teacher,
    make_year,
)


def _stats_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/stats"


# ---------------------------------------------------------------------------
# -- Auth / project decorators
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_stats_url(project.pk))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_stats_url(project.pk + 1000))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


# ---------------------------------------------------------------------------
# -- Counts
# ---------------------------------------------------------------------------


def test_empty_db_reports_all_zero(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_stats_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "rooms": 0,
        "teachers": 0,
        "degrees": 0,
        "years": 0,
        "subjects": 0,
        "classes": 0,
        "sessions": 0,
    }


def test_seeded_db_reports_each_count(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # One degree with two years; the second year is built off the same degree.
    degree = make_degree(project_db)
    year = make_year(project_db, degree=degree, number=1)
    make_year(project_db, degree=degree, number=2)

    # Two classes and three subjects, all attached to the first year.
    klass = make_class(project_db, year=year, code="1LEIC01")
    make_class(project_db, year=year, code="1LEIC02")
    subject = make_subject(project_db, year=year)
    make_subject(project_db, year=year)
    make_subject(project_db, year=year)

    # Two rooms and one teacher.
    make_room(project_db, name="B101")
    make_room(project_db, name="B102")
    make_teacher(project_db)

    # Two sessions, one of them wired to a class/subject.
    session_row = make_session(project_db)
    make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = auth_client.get(_stats_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "rooms": 2,
        "teachers": 1,
        "degrees": 1,
        "years": 2,
        "subjects": 3,
        "classes": 2,
        "sessions": 2,
    }


def test_stats_envelope_carries_message_and_timestamp(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_stats_url(project.pk))

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Stats retrieved successfully"
    assert "timestamp" in body
    assert "data" in body
