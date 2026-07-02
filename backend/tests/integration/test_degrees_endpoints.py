"""Integration tests for the project *degrees* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/degrees/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/degrees/<degree_id>`` — the detail view (years with
  per-year stats, sorted by year number), including the 404 for an unknown
  degree id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``DegreeDAO`` + ``YearDAO`` + the response schemas. Order-independent facts
are compared as lookup dicts; the year ordering in the detail view *is*
asserted since that endpoint sorts by number. The volatile ``timestamp`` is
only checked for presence.
"""

import uuid

from django.test import Client
from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.models._secondary_tables import subject_years
from tests.factories import (
    make_class,
    make_degree,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)


def _list_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/degrees/"


def _detail_url(project_id: int, degree_id) -> str:
    return f"/api/projects/{project_id}/degrees/{degree_id}"


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
    assert response.json()["error"] == "auth.not_authenticated"


# ---------------------------------------------------------------------------
# -- List
# ---------------------------------------------------------------------------


def test_list_empty_db(auth_client: Client, project: Project, project_db: Session) -> None:
    response = auth_client.get(_list_url(project.pk))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["degrees"] == []
    assert data["count"] == 0


def test_list_reports_aggregate_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Degree A: one year with a subject, a class and a session.
    degree_a = make_degree(project_db, acronym="LEIC", name="Engenharia Informática")
    year_a = make_year(project_db, degree=degree_a, number=1)
    subject_a = make_subject(project_db, year=year_a)
    class_a = make_class(project_db, year=year_a)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class_a,
        subject=subject_a,
    )
    # Degree B: no years, subjects, classes or sessions.
    degree_b = make_degree(project_db, acronym="MIEEC", name="Engenharia Eletrotécnica")

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 2
    by_acronym = {d["acronym"]: d for d in data["degrees"]}
    assert by_acronym.keys() == {"LEIC", "MIEEC"}

    populated = by_acronym["LEIC"]
    assert populated["id"] == str(degree_a.id)
    assert populated["name"] == "Engenharia Informática"
    assert populated["years"] == 1
    assert populated["subjects"] == 1
    assert populated["classes"] == 1
    assert populated["sessions"] == 1

    empty = by_acronym["MIEEC"]
    assert empty["id"] == str(degree_b.id)
    assert empty["years"] == 0
    assert empty["subjects"] == 0
    assert empty["classes"] == 0
    assert empty["sessions"] == 0


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_degree_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.degrees.not_found"


def test_detail_returns_years_sorted_with_stats(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    degree = make_degree(project_db, acronym="LEIC", name="Engenharia Informática")
    # Seed the second year first to prove the endpoint sorts by number.
    year_2 = make_year(project_db, degree=degree, number=2)
    year_1 = make_year(project_db, degree=degree, number=1)

    subject = make_subject(project_db, year=year_1)
    klass = make_class(project_db, year=year_1)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = auth_client.get(_detail_url(project.pk, degree.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(degree.id)
    assert data["acronym"] == "LEIC"
    assert data["name"] == "Engenharia Informática"

    years = data["years"]
    # Sorted ascending by number.
    assert [y["number"] for y in years] == [1, 2]
    assert [y["id"] for y in years] == [str(year_1.id), str(year_2.id)]
    assert all(y["degree_id"] == str(degree.id) for y in years)

    first, second = years
    assert first["subjects"] == 1
    assert first["classes"] == 1
    assert first["sessions"] == 1
    assert second["subjects"] == 0
    assert second["classes"] == 0
    assert second["sessions"] == 0


def test_detail_degree_without_years_has_empty_list(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    degree = make_degree(project_db, acronym="LEIC")

    response = auth_client.get(_detail_url(project.pk, degree.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(degree.id)
    assert data["years"] == []


# ---------------------------------------------------------------------------
# -- Wrong HTTP method
# ---------------------------------------------------------------------------


def test_list_and_detail_reject_post_with_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # The views only define get(); Django's View refuses every write method.
    list_response = auth_client.post(_list_url(project.pk))
    assert list_response.status_code == 405

    detail_response = auth_client.post(_detail_url(project.pk, uuid.uuid7()))
    assert detail_response.status_code == 405


# ---------------------------------------------------------------------------
# -- Unknown project on the detail route
# ---------------------------------------------------------------------------


def test_detail_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_detail_url(project.pk + 1000, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


# ---------------------------------------------------------------------------
# -- Cross-project / cross-user isolation
# ---------------------------------------------------------------------------


def test_detail_degree_id_from_other_project_is_not_returned(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    # Same-type entity seeded in BOTH per-project SQLite files.
    degree_a = make_degree(project_db, acronym="LEIC", name="Informática")
    make_degree(second_project_db, acronym="MIEEC", name="Eletrotécnica")

    # Project A's degree id, requested under project B, must not leak across DBs.
    response = auth_client.get(_detail_url(second_project.pk, degree_a.id))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.degrees.not_found"


def test_detail_non_owner_still_gets_the_degree(
    other_auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # NOTE: access is intentionally NOT owner-scoped. ``require_project`` only
    # checks that the project exists, so a logged-in non-owner still gets 200 +
    # the owner's data. This test locks in that shared-access behavior.
    degree = make_degree(project_db, acronym="LEIC", name="Informática")

    response = other_auth_client.get(_detail_url(project.pk, degree.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(degree.id)
    assert data["acronym"] == "LEIC"
    assert data["name"] == "Informática"


# ---------------------------------------------------------------------------
# -- Degree-level dedup of shared subject / session
# ---------------------------------------------------------------------------


def test_list_degree_counts_dedup_shared_subject_and_session(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Degree A: two years share ONE subject, and ONE session is attended by two
    # classes (one per year). ``get_all_with_stats`` dedups via
    # count(distinct subject_id) and count(distinct session_id).
    degree_a = make_degree(project_db, acronym="LEIC", name="Informática", commit=False)
    year_1 = make_year(project_db, degree=degree_a, number=1, commit=False)
    year_2 = make_year(project_db, degree=degree_a, number=2, commit=False)

    subject = make_subject(project_db, year=year_1, commit=False)
    # Link the same subject to the second year -> two subject_years rows.
    project_db.execute(
        insert(subject_years).values(subject_id=subject.id, year_id=year_2.id),
    )

    class_1 = make_class(project_db, year=year_1, commit=False)
    class_2 = make_class(project_db, year=year_2, commit=False)
    shared_session = make_session(project_db, commit=False)
    make_session_class_subject(
        project_db,
        session_row=shared_session,
        class_row=class_1,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=shared_session,
        class_row=class_2,
        subject=subject,
        commit=False,
    )

    # Degree B: an unrelated degree with its own subject, class and session, to
    # prove its rows are EXCLUDED from degree A's counts (and vice versa).
    degree_b = make_degree(project_db, acronym="MIEEC", name="Eletrotécnica", commit=False)
    year_b = make_year(project_db, degree=degree_b, number=1, commit=False)
    subject_b = make_subject(project_db, year=year_b, commit=False)
    class_b = make_class(project_db, year=year_b, commit=False)
    session_b = make_session(project_db, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b,
        subject=subject_b,
        commit=False,
    )
    project_db.commit()

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 2
    by_acronym = {d["acronym"]: d for d in data["degrees"]}
    assert by_acronym.keys() == {"LEIC", "MIEEC"}

    populated = by_acronym["LEIC"]
    assert populated["id"] == str(degree_a.id)
    assert populated["years"] == 2  # two distinct Year rows
    assert populated["subjects"] == 1  # one subject, deduped across two years
    assert populated["classes"] == 2  # two distinct Class rows (not deduped)
    assert populated["sessions"] == 1  # one session, deduped across two classes

    # The unrelated degree keeps its own counts; nothing leaked either way.
    other = by_acronym["MIEEC"]
    assert other["id"] == str(degree_b.id)
    assert other["years"] == 1
    assert other["subjects"] == 1
    assert other["classes"] == 1
    assert other["sessions"] == 1
