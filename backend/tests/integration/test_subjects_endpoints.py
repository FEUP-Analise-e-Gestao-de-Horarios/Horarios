"""Integration tests for the project *subjects* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/subjects/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/subjects/<subject_id>`` — the detail view (years +
  owning degree, week blocks), including the 404 for an unknown subject id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``SubjectDAO`` + the response schemas. Order-independent facts are compared
as sets or lookup dicts; the volatile ``timestamp`` is only checked for
presence.
"""

import datetime
import uuid

from django.test import Client
from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.models._secondary_tables import subject_years
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    make_class,
    make_degree,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)


def _list_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/subjects/"


def _detail_url(project_id: int, subject_id) -> str:
    return f"/api/projects/{project_id}/subjects/{subject_id}"


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
    assert data["subjects"] == []
    assert data["count"] == 0


def test_list_reports_session_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    year_a = make_year(project_db, degree=make_degree(project_db, acronym="LEIC"))
    subject = make_subject(
        project_db,
        year=year_a,
        code="UC-A",
        acronym="PROG",
        name="Programação",
    )
    klass = make_class(project_db, year=year_a)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    # A second subject (own degree) with no sessions, to check the 0 count.
    year_b = make_year(project_db, degree=make_degree(project_db, acronym="MIEEC"))
    make_subject(project_db, year=year_b, code="UC-B", acronym="MATH", name="Matemática")

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 2
    by_code = {s["code"]: s for s in data["subjects"]}
    assert by_code.keys() == {"UC-A", "UC-B"}
    assert by_code["UC-A"]["sessions"] == 1
    assert by_code["UC-A"]["acronym"] == "PROG"
    assert by_code["UC-A"]["name"] == "Programação"
    assert by_code["UC-A"]["id"] == str(subject.id)
    assert by_code["UC-B"]["sessions"] == 0


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_subject_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.subjects.not_found"


def test_detail_returns_years_degree_and_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    degree = make_degree(project_db, acronym="LEIC", name="Engenharia Informática")
    year = make_year(project_db, degree=degree, number=1)
    subject = make_subject(project_db, year=year, code="UC-A")
    klass = make_class(project_db, year=year, code="1LEIC01")
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )

    response = auth_client.get(_detail_url(project.pk, subject.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(subject.id)
    assert data["code"] == "UC-A"
    # One year, carrying its owning degree.
    assert len(data["years"]) == 1
    year_entry = data["years"][0]
    assert year_entry["id"] == str(year.id)
    assert year_entry["degree_id"] == str(degree.id)
    assert year_entry["number"] == 1
    assert year_entry["degree"]["id"] == str(degree.id)
    assert year_entry["degree"]["acronym"] == "LEIC"
    # One week block, containing the seeded session.
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert len(block["sessions"]) == 1
    session_details = block["sessions"][0]
    assert session_details["id"] == str(session_row.id)
    assert [s["id"] for s in session_details["subjects"]] == [str(subject.id)]
    assert [c["code"] for c in session_details["classes"]] == ["1LEIC01"]


def test_detail_without_sessions_has_empty_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    subject = make_subject(project_db, code="UC-A")

    response = auth_client.get(_detail_url(project.pk, subject.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "UC-A"
    assert len(data["years"]) == 1
    assert data["blocks"] == []


def test_detail_subject_in_multiple_years_returns_all_years_with_degrees(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A subject taught across two years belonging to two *different* degrees:
    # exercises the ``Subject.years`` m2m fan-out and the per-year nested degree.
    degree_a = make_degree(project_db, acronym="LEIC", name="Engenharia Informática")
    degree_b = make_degree(project_db, acronym="MIEEC", name="Engenharia Eletrotécnica")
    year_a = make_year(project_db, degree=degree_a, number=1)
    year_b = make_year(project_db, degree=degree_b, number=2)

    subject = make_subject(project_db, year=year_a, code="UC-A")
    # Link the same subject to a second year (of a different degree).
    project_db.execute(
        insert(subject_years).values(subject_id=subject.id, year_id=year_b.id),
    )
    project_db.commit()

    response = auth_client.get(_detail_url(project.pk, subject.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(subject.id)

    # Both years fan out, each carrying its own owning degree.
    assert len(data["years"]) == 2
    by_year = {y["id"]: y for y in data["years"]}
    assert by_year.keys() == {str(year_a.id), str(year_b.id)}

    entry_a = by_year[str(year_a.id)]
    assert entry_a["number"] == 1
    assert entry_a["degree_id"] == str(degree_a.id)
    assert entry_a["degree"]["id"] == str(degree_a.id)
    assert entry_a["degree"]["acronym"] == "LEIC"
    assert entry_a["degree"]["name"] == "Engenharia Informática"

    entry_b = by_year[str(year_b.id)]
    assert entry_b["number"] == 2
    assert entry_b["degree_id"] == str(degree_b.id)
    assert entry_b["degree"]["id"] == str(degree_b.id)
    assert entry_b["degree"]["acronym"] == "MIEEC"
    assert entry_b["degree"]["name"] == "Engenharia Eletrotécnica"

    # The two distinct owning degrees both surface, and nothing collapses them.
    assert {y["degree"]["id"] for y in data["years"]} == {str(degree_a.id), str(degree_b.id)}
    assert {y["degree"]["acronym"] for y in data["years"]} == {"LEIC", "MIEEC"}


def test_detail_malformed_uuid_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # A non-UUID id segment must fail the ``<uuid:subject_id>`` converter and
    # 404 (no route match) rather than 500 or a mis-parse.
    response = auth_client.get(_detail_url(project.pk, "not-a-uuid"))
    assert response.status_code == 404


def test_list_session_count_dedups_same_session_across_classes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # One session shared by two classes for the same subject: the stats query
    # counts ``distinct(session_id)`` so the subject reports 1 session, not 2.
    year = make_year(project_db, degree=make_degree(project_db, acronym="LEIC"))
    subject = make_subject(project_db, year=year, code="UC-A")
    class_a = make_class(project_db, year=year, code="C-A")
    class_b = make_class(project_db, year=year, code="C-B")
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class_a,
        subject=subject,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class_b,
        subject=subject,
    )
    # An unrelated subject with no sessions must stay at 0 (false-positive guard).
    make_subject(project_db, year=year, code="UC-B")

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    by_code = {s["code"]: s for s in data["subjects"]}
    assert by_code.keys() == {"UC-A", "UC-B"}
    assert by_code["UC-A"]["sessions"] == 1
    assert by_code["UC-B"]["sessions"] == 0


def test_detail_blocks_group_weeks_and_dedup_session_entities(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    # Two consecutive weeks with an identical session (same subject taught to two
    # classes) collapse into a single WeekBlock spanning both weeks, and the
    # representative session dedups the subject across its two class rows.
    degree = make_degree(project_db, acronym="LEIC")
    year = make_year(project_db, degree=degree)
    subject = make_subject(project_db, year=year, code="UC-A")
    class_a = make_class(project_db, year=year, code="1LEIC01")
    class_b = make_class(project_db, year=year, code="1LEIC02")

    week_one = datetime.date(2025, 9, 15)
    week_two = datetime.date(2025, 9, 22)
    for wk in (week_one, week_two):
        session_row = make_session(
            project_db,
            week=wk,
            weekday=WeekDay.MONDAY,
            start_time=9,
            duration=2,
            type="T",
        )
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_a,
            subject=subject,
        )
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_b,
            subject=subject,
        )

    response = auth_client.get(_detail_url(project.pk, subject.id))

    assert response.status_code == 200
    data = response.json()["data"]

    # Identical timetables in both weeks -> one block covering both weeks.
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert block["weeks"] == [week_one.isoformat(), week_two.isoformat()]

    # One representative session; its subject list is deduped to a single entry
    # while both classes are preserved.
    assert len(block["sessions"]) == 1
    session_details = block["sessions"][0]
    assert [s["id"] for s in session_details["subjects"]] == [str(subject.id)]
    assert {c["code"] for c in session_details["classes"]} == {"1LEIC01", "1LEIC02"}
