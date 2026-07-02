"""Integration tests for the project *years* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/years/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/years/<year_id>`` — the detail view (subjects and
  classes, each with their session counts), including the 404 for an unknown
  year id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``YearDAO`` + the response schemas. Order-independent facts are compared via
lookup dicts; the volatile ``timestamp`` is only checked for presence.
"""

import uuid

import pytest
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
    return f"/api/projects/{project_id}/years/"


def _detail_url(project_id: int, year_id) -> str:
    return f"/api/projects/{project_id}/years/{year_id}"


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
    assert data["years"] == []
    assert data["count"] == 0


def test_list_reports_subject_class_and_session_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A single degree owns both years (``Degree.acronym`` is unique, so the two
    # years cannot each auto-create their own default degree).
    degree = make_degree(project_db)
    year = make_year(project_db, degree=degree, number=1)
    klass = make_class(project_db, year=year, code="1LEIC01")
    subject = make_subject(project_db, year=year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    # A second, empty year under the same degree, to check the 0 counts.
    make_year(project_db, degree=degree, number=2)

    response = auth_client.get(_list_url(project.pk))

    data = response.json()["data"]
    assert data["count"] == 2
    by_number = {y["number"]: y for y in data["years"]}
    assert by_number[1]["subjects"] == 1
    assert by_number[1]["classes"] == 1
    assert by_number[1]["sessions"] == 1
    assert by_number[1]["id"] == str(year.id)
    assert by_number[1]["degree_id"] == str(degree.id)
    assert by_number[2]["subjects"] == 0
    assert by_number[2]["classes"] == 0
    assert by_number[2]["sessions"] == 0


def test_list_shared_subject_counts_in_both_years_without_double_counting_sessions(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # One subject taught in TWO years of the same degree, linked to each via the
    # ``subject_years`` m2m. Its only session is attended by a class that lives
    # in year A. This exercises the DAO's documented no-double-count branch:
    # subjects are m2m-driven (counted in every year they are linked to), while
    # sessions are class-driven (counted only in the year owning the class).
    degree = make_degree(project_db)
    year_a = make_year(project_db, degree=degree, number=1)
    year_b = make_year(project_db, degree=degree, number=2)

    subject = make_subject(project_db, year=year_a)
    # Second m2m link so the same UC also belongs to year B.
    project_db.execute(
        insert(subject_years).values(subject_id=subject.id, year_id=year_b.id),
    )
    project_db.commit()

    # The shared UC's session is attended by a class in year A only.
    klass = make_class(project_db, year=year_a, code="1LEIC01")
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 2
    by_number = {y["number"]: y for y in data["years"]}

    # The shared UC is counted once in EACH year it is linked to (not skipped,
    # not merged) — one subject in year A and one in year B.
    assert by_number[1]["subjects"] == 1
    assert by_number[2]["subjects"] == 1

    # Only year A owns a class; year B has none.
    assert by_number[1]["classes"] == 1
    assert by_number[2]["classes"] == 0

    # Sessions are class-driven: the lone session belongs to year A and is NOT
    # double-counted into year B despite the subject being shared across both.
    assert by_number[1]["sessions"] == 1
    assert by_number[2]["sessions"] == 0


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_year_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.years.not_found"


def test_detail_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_detail_url(project.pk + 1000, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_detail_returns_sorted_subjects_and_classes_with_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year = make_year(project_db, number=3)
    # Seeded high-number first to prove the endpoint sorts subjects by number.
    subject_high = make_subject(
        project_db,
        year=year,
        number=20,
        code="M.EIC020",
        acronym="AAA",
        name="Algorithms",
    )
    subject_low = make_subject(
        project_db,
        year=year,
        number=10,
        code="M.EIC010",
        acronym="PRG",
        name="Programming",
    )
    # Seeded out of code order to prove the endpoint sorts classes by code.
    make_class(project_db, year=year, code="2MEIC02")
    klass_first = make_class(project_db, year=year, code="1MEIC01")

    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass_first,
        subject=subject_low,
    )

    response = auth_client.get(_detail_url(project.pk, year.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(year.id)
    assert data["degree_id"] == str(year.degree_id)
    assert data["number"] == 3

    # Subjects come back sorted by ``number`` ascending.
    assert [s["number"] for s in data["subjects"]] == [10, 20]
    subjects_by_code = {s["code"]: s for s in data["subjects"]}
    assert subjects_by_code["M.EIC010"]["id"] == str(subject_low.id)
    assert subjects_by_code["M.EIC010"]["acronym"] == "PRG"
    assert subjects_by_code["M.EIC010"]["name"] == "Programming"
    assert subjects_by_code["M.EIC010"]["sessions"] == 1
    assert subjects_by_code["M.EIC020"]["id"] == str(subject_high.id)
    assert subjects_by_code["M.EIC020"]["sessions"] == 0

    # Classes come back sorted by ``code`` ascending.
    assert [c["code"] for c in data["classes"]] == ["1MEIC01", "2MEIC02"]
    classes_by_code = {c["code"]: c for c in data["classes"]}
    assert classes_by_code["1MEIC01"]["id"] == str(klass_first.id)
    assert classes_by_code["1MEIC01"]["year_id"] == str(year.id)
    assert classes_by_code["1MEIC01"]["sessions"] == 1
    assert classes_by_code["2MEIC02"]["sessions"] == 0


def test_detail_empty_subjects_and_classes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A bare year with no subjects and no classes: the detail view still returns
    # 200 with the year/degree fields and empty ``subjects``/``classes`` lists,
    # covering the empty-sort branches of the view.
    year = make_year(project_db, number=5)

    response = auth_client.get(_detail_url(project.pk, year.id))

    assert response.status_code == 200
    body = response.json()
    assert "timestamp" in body
    data = body["data"]
    assert data["id"] == str(year.id)
    assert data["degree_id"] == str(year.degree_id)
    assert data["number"] == 5
    assert data["subjects"] == []
    assert data["classes"] == []


def test_detail_excludes_other_years_subjects_and_classes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Year detail is year-scoped: another year's subjects and classes are excluded."""
    degree = make_degree(project_db)
    year_a = make_year(project_db, degree=degree, number=1)
    year_b = make_year(project_db, degree=degree, number=2)

    # Year A owns its subject and class.
    subject_a = make_subject(project_db, year=year_a, code="UC-A")
    class_a = make_class(project_db, year=year_a, code="1LEIC0A")

    # Year B owns a completely distinct subject and class, which must not leak.
    subject_b = make_subject(project_db, year=year_b, code="UC-B")
    class_b = make_class(project_db, year=year_b, code="2LEIC0B")

    response = auth_client.get(_detail_url(project.pk, year_a.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(year_a.id)
    # Only year A's subject and class are present; year B's are excluded.
    assert {s["id"] for s in data["subjects"]} == {str(subject_a.id)}
    assert {c["id"] for c in data["classes"]} == {str(class_a.id)}
    assert str(subject_b.id) not in {s["id"] for s in data["subjects"]}
    assert str(class_b.id) not in {c["id"] for c in data["classes"]}


# ---------------------------------------------------------------------------
# -- Read-only routes reject mutating verbs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_return_405(
    method: str,
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Both views define only get(); every write verb falls through to 405."""
    for url in (_list_url(project.pk), _detail_url(project.pk, uuid.uuid7())):
        response = getattr(auth_client, method)(url)
        assert response.status_code == 405
        assert "GET" in response.headers["Allow"]
