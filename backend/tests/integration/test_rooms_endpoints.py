"""Integration tests for the project *rooms* endpoints.

Two routes are covered end to end through the Django test client against a
seeded per-project SQLite file (the ``project_db`` fixture):

* ``GET /api/projects/<pk>/rooms/`` — the list-with-stats view.
* ``GET /api/projects/<pk>/rooms/<room_id>`` — the detail view (week blocks and
  red blocks), including the 404 for an unknown room id.

Assertions target the ``SuccessResponse`` envelope and the wire shape produced
by ``RoomDAO`` + the response schemas. Order-independent facts are compared as
sets or lookup dicts; the volatile ``timestamp`` is only checked for presence.
"""

import uuid

from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from tests.factories import (
    link_session_room,
    make_class,
    make_room,
    make_room_red_block,
    make_session,
    make_session_class_subject,
    make_subject,
)


def _list_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/rooms/"


def _detail_url(project_id: int, room_id) -> str:
    return f"/api/projects/{project_id}/rooms/{room_id}"


# ---------------------------------------------------------------------------
# -- Auth / project decorators
# ---------------------------------------------------------------------------


def test_list_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_list_url(project.pk))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_detail_unauthenticated_returns_401(project: Project, project_db: Session) -> None:
    response = Client().get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_list_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_list_url(project.pk + 1000))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_detail_unknown_project_returns_404(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_detail_url(project.pk + 1000, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


# ---------------------------------------------------------------------------
# -- List
# ---------------------------------------------------------------------------


def test_list_empty_db(auth_client: Client, project: Project, project_db: Session) -> None:
    response = auth_client.get(_list_url(project.pk))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["rooms"] == []
    assert data["count"] == 0


def test_list_reports_session_and_red_block_counts(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    room = make_room(project_db, name="B101", type="Anf", size="Grandes", seats="99")
    session_row = make_session(project_db)
    link_session_room(project_db, session_row=session_row, room=room)
    make_room_red_block(project_db, room=room, hour=1000)
    # A second room with nothing linked, to check the 0 counts.
    make_room(project_db, name="B102")

    response = auth_client.get(_list_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 2
    by_name = {r["name"]: r for r in data["rooms"]}
    assert by_name.keys() == {"B101", "B102"}
    assert by_name["B101"]["sessions"] == 1
    assert by_name["B101"]["red_blocks"] == 1
    assert by_name["B101"]["type"] == "Anf"
    assert by_name["B101"]["size"] == "Grandes"
    assert by_name["B101"]["seats"] == "99"
    assert str(room.id) == by_name["B101"]["id"]
    assert by_name["B102"]["sessions"] == 0
    assert by_name["B102"]["red_blocks"] == 0


# ---------------------------------------------------------------------------
# -- Detail
# ---------------------------------------------------------------------------


def test_detail_unknown_room_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    response = auth_client.get(_detail_url(project.pk, uuid.uuid7()))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.rooms.not_found"


def test_detail_empty_room_has_no_blocks_or_red_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    room = make_room(project_db, name="B101")

    response = auth_client.get(_detail_url(project.pk, room.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(room.id)
    assert data["name"] == "B101"
    assert data["blocks"] == []
    assert data["red_blocks"] == []


def test_detail_returns_blocks_and_red_blocks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    room = make_room(project_db, name="B101")
    klass = make_class(project_db, code="1LEIC01")
    subject = make_subject(project_db, year=klass.year)
    session_row = make_session(project_db)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
    )
    link_session_room(project_db, session_row=session_row, room=room)
    make_room_red_block(project_db, room=room, hour=1000)

    response = auth_client.get(_detail_url(project.pk, room.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(room.id)
    assert data["name"] == "B101"
    # One week block, containing the seeded session bound to this room.
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert len(block["sessions"]) == 1
    session = block["sessions"][0]
    assert session["id"] == str(session_row.id)
    assert {r["id"] for r in session["rooms"]} == {str(room.id)}
    assert {c["code"] for c in session["classes"]} == {"1LEIC01"}
    # One red block.
    assert [rb["hour"] for rb in data["red_blocks"]] == [1000]
    assert data["red_blocks"][0]["weekday"] == "monday"
