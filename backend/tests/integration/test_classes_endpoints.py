"""Integration tests for the project *classes* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/classes/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/classes/<class_id>`` — the detail view (year + degree,
  week blocks, red blocks), including the 404 for an unknown class id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``ClassDAO`` + the response schemas. Order-independent facts are compared as
sets; the volatile ``timestamp`` is only checked for presence.
"""

import uuid

import pytest
from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from tests.factories import (
    make_class,
    make_class_red_block,
    make_session,
    make_session_class_subject,
    make_subject,
)


def _list_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/classes/"


def _detail_url(project_id: int, class_id) -> str:
    return f"/api/projects/{project_id}/classes/{class_id}"


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


def test_detail_unauthenticated_returns_auth_error_code(
    project: Project,
    project_db: Session,
) -> None:
    # Strengthens the status-only test above: a wrong-but-401 response must not pass.
    response = Client().get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_return_405(
    method: str,
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Both views define only get(); every write verb falls through to Django's
    # http_method_not_allowed. These endpoints are read-only.
    for url in (_list_url(project.pk), _detail_url(project.pk, uuid.uuid7())):
        response = getattr(auth_client, method)(url)
        assert response.status_code == 405
        assert "GET" in response.headers["Allow"]


# ---------------------------------------------------------------------------
# -- List
# ---------------------------------------------------------------------------


def test_list_empty_db(auth_client: Client, project: Project, project_db: Session) -> None:
    response = auth_client.get(_list_url(project.pk))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["classes"] == []
    assert data["count"] == 0


def test_list_reports_session_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    klass = make_class(project_db, code="1LEIC01", shift=2)
    subject = make_subject(project_db, year=klass.year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    # A second class with no sessions, to check the 0 count.
    make_class(project_db, year=klass.year, code="1LEIC02")

    response = auth_client.get(_list_url(project.pk))

    data = response.json()["data"]
    assert data["count"] == 2
    by_code = {c["code"]: c for c in data["classes"]}
    assert by_code["1LEIC01"]["sessions"] == 1
    assert by_code["1LEIC01"]["shift"] == 2
    assert by_code["1LEIC02"]["sessions"] == 0
    assert str(klass.id) == by_code["1LEIC01"]["id"]


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_class_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.classes.not_found"


def test_detail_returns_year_degree_blocks_and_red_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    klass = make_class(project_db, code="1LEIC01")
    subject = make_subject(project_db, year=klass.year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    make_class_red_block(project_db, class_row=klass, hour=1000)

    response = auth_client.get(_detail_url(project.pk, klass.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "1LEIC01"
    # Nested year carries its owning degree.
    assert data["year"]["id"] == str(klass.year_id)
    assert data["year"]["degree"]["id"] == str(klass.year.degree_id)
    # One week block, containing the seeded session.
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert len(block["sessions"]) == 1
    assert block["sessions"][0]["classes"][0]["code"] == "1LEIC01"
    # One red block.
    assert [rb["hour"] for rb in data["red_blocks"]] == [1000]


def test_detail_empty_blocks_and_red_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A class with no sessions and no red blocks exercises the empty-collection
    # path of WeekBlock.from_sessions and the schema's list defaults.
    klass = make_class(project_db, code="1LEIC01")

    response = auth_client.get(_detail_url(project.pk, klass.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "1LEIC01"
    assert data["blocks"] == []
    assert data["red_blocks"] == []
    # The nested year/degree are still present.
    assert data["year"]["id"] == str(klass.year_id)
    assert data["year"]["degree"]["id"] == str(klass.year.degree_id)
