"""End-to-end tests for the confirmed-group DELETE endpoints.

Two verbs are exercised here against a seeded per-project SQLAlchemy file (the
``project_db`` fixture); the endpoint opens its own session against the same
file, so seeded rows are committed before the request and re-read fresh
(``expire_all``) afterwards.

* ``DELETE /api/projects/<pk>/parallel-blocks/groups/`` -- clears *every*
  confirmed member, returns the number of rows removed as ``data`` (a JSON
  int), and flips ``Project.has_selected_parallel_sessions`` to ``True`` (even
  on an empty DB).
* ``DELETE /api/projects/<pk>/parallel-blocks/groups/<group_id>`` -- deletes one
  group. ``data`` is ``null`` on success; a group id matching no member rows
  yields 404 ``projects.parallel_groups.not_found``. It does **not** touch the
  flag.

Pure delete tests need no real candidates -- raw membership rows seeded via
``make_group_member`` are enough.
"""

import datetime
import uuid
from uuid import UUID

from django.test import Client
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.models import ParallelBlockGroupMember
from tests.factories import make_group_member


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------
def _groups_url(project_id: int) -> str:
    """The confirmed-groups collection URL (always with a trailing slash)."""
    return f"/api/projects/{project_id}/parallel-blocks/groups/"


def _group_url(project_id: int, group_id: UUID | str) -> str:
    """The single-group URL (no trailing slash: ``groups/<uuid:group_id>``)."""
    return f"/api/projects/{project_id}/parallel-blocks/groups/{group_id}"


def _all_members(db_session: Session) -> list[ParallelBlockGroupMember]:
    """Read every membership row through a fresh view of the committed state."""
    db_session.expire_all()
    return list(db_session.scalars(select(ParallelBlockGroupMember)).all())


def _groups_by_id(db_session: Session) -> dict[UUID, set[UUID]]:
    """Map ``parallel_block_group_id`` -> set of member ``original_block_id``."""
    groups: dict[UUID, set[UUID]] = {}
    for row in _all_members(db_session):
        groups.setdefault(row.parallel_block_group_id, set()).add(row.original_block_id)
    return groups


def _flag(project_id: int) -> bool:
    """Reload the Django ``Project`` and return its parallel-selection flag."""
    return Project.objects.get(pk=project_id).has_selected_parallel_sessions


def _seed_group(db_session: Session, *, size: int = 2) -> tuple[UUID, set[UUID]]:
    """Seed one confirmed group with ``size`` members; return ``(group_id, block_ids)``."""
    group_id = uuid.uuid7()
    block_ids = {uuid.uuid7() for _ in range(size)}
    members = list(block_ids)
    for block_id in members[:-1]:
        make_group_member(db_session, group_id=group_id, original_block_id=block_id, commit=False)
    make_group_member(db_session, group_id=group_id, original_block_id=members[-1])
    return group_id, block_ids


# ---------------------------------------------------------------------------
# -- Clear-all: DELETE /groups/
# ---------------------------------------------------------------------------
def test_clear_all_removes_all_and_flips_flag(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two seeded groups: DELETE returns the row count, empties the table, flag True."""
    _g1, blocks_1 = _seed_group(project_db, size=2)
    _g2, blocks_2 = _seed_group(project_db, size=3)
    total_rows = len(blocks_1) + len(blocks_2)

    response = auth_client.delete(_groups_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == total_rows
    assert isinstance(data, int)
    assert not isinstance(data, bool)
    assert _all_members(project_db) == []
    assert _flag(project.pk) is True


def test_clear_all_on_empty_db_returns_zero(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Clearing an already-empty DB -> 200, data 0, no rows, flag still flipped True."""
    response = auth_client.delete(_groups_url(project.pk))

    assert response.status_code == 200
    assert response.json()["data"] == 0
    assert _all_members(project_db) == []
    assert _flag(project.pk) is True


def test_clear_all_scoped_to_this_project(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    """Clearing project A touches only A's DB; project B's rows survive."""
    _ga, blocks_a = _seed_group(project_db, size=2)
    gb, blocks_b = _seed_group(second_project_db, size=2)

    response = auth_client.delete(_groups_url(project.pk))

    assert response.status_code == 200
    assert response.json()["data"] == len(blocks_a)
    assert _all_members(project_db) == []
    # Project B's own file is untouched.
    assert _groups_by_id(second_project_db) == {gb: blocks_b}


def test_clear_all_envelope_shape_and_int_data(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Clear-all envelope is {timestamp, message, data}; data is an int, not a bool."""
    _seed_group(project_db, size=2)

    response = auth_client.delete(_groups_url(project.pk))

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert isinstance(payload["data"], int)
    assert not isinstance(payload["data"], bool)
    assert isinstance(payload["message"], str) and payload["message"]
    datetime.datetime.fromisoformat(payload["timestamp"])


# ---------------------------------------------------------------------------
# -- Delete-one: DELETE /groups/<group_id>
# ---------------------------------------------------------------------------
def test_delete_one_removes_only_that_group(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Deleting one group by id -> 200 data null; the other group survives intact."""
    g1, blocks_1 = _seed_group(project_db, size=2)
    g2, blocks_2 = _seed_group(project_db, size=3)

    response = auth_client.delete(_group_url(project.pk, g1))

    assert response.status_code == 200
    assert response.json()["data"] is None
    assert _groups_by_id(project_db) == {g2: blocks_2}
    assert blocks_1.isdisjoint(
        {b for members in _groups_by_id(project_db).values() for b in members},
    )


def test_delete_one_unknown_group_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A group id matching no member rows -> 404 not_found; existing rows survive."""
    g1, blocks_1 = _seed_group(project_db, size=2)

    response = auth_client.delete(_group_url(project.pk, uuid.uuid7()))

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "projects.parallel_groups.not_found"
    assert body["message"] == "Parallel group not found."
    assert _groups_by_id(project_db) == {g1: blocks_1}


def test_delete_one_twice_second_is_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Re-deleting an already-emptied group id -> 404 (no rows left to match)."""
    g1, _blocks_1 = _seed_group(project_db, size=2)

    first = auth_client.delete(_group_url(project.pk, g1))
    assert first.status_code == 200
    assert first.json()["data"] is None

    second = auth_client.delete(_group_url(project.pk, g1))
    assert second.status_code == 404
    assert second.json()["error"] == "projects.parallel_groups.not_found"
    assert _all_members(project_db) == []


def test_delete_one_does_not_change_flag(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A successful delete-one leaves ``has_selected_parallel_sessions`` untouched."""
    g1, _blocks_1 = _seed_group(project_db, size=2)
    assert _flag(project.pk) is False  # default on a fresh project

    response = auth_client.delete(_group_url(project.pk, g1))

    assert response.status_code == 200
    assert _flag(project.pk) is False


def test_delete_one_envelope_shape_data_null(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Delete-one envelope is {timestamp, message, data}; data is null."""
    g1, _blocks_1 = _seed_group(project_db, size=2)

    response = auth_client.delete(_group_url(project.pk, g1))

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert payload["data"] is None
    assert isinstance(payload["message"], str) and payload["message"]
    datetime.datetime.fromisoformat(payload["timestamp"])


# ---------------------------------------------------------------------------
# -- Decorators (auth / project) and routing
# ---------------------------------------------------------------------------
def test_unauthenticated_clear_all_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """Unauthenticated clear-all -> 401 before any DB access; nothing removed."""
    _g1, blocks_1 = _seed_group(project_db, size=2)
    group_id = next(iter(_groups_by_id(project_db)))

    response = Client().delete(_groups_url(project.pk))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _groups_by_id(project_db) == {group_id: blocks_1}
    assert _flag(project.pk) is False


def test_unauthenticated_delete_one_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """Unauthenticated delete-one -> 401 before any DB access; nothing removed."""
    g1, blocks_1 = _seed_group(project_db, size=2)

    response = Client().delete(_group_url(project.pk, g1))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _groups_by_id(project_db) == {g1: blocks_1}


def test_unknown_project_clear_all_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Clear-all on a nonexistent project id -> 404 from require_project."""
    response = auth_client.delete(_groups_url(project.pk + 1000))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_unknown_project_delete_one_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Delete-one on a nonexistent project id -> 404 from require_project."""
    response = auth_client.delete(_group_url(project.pk + 1000, uuid.uuid7()))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_non_uuid_group_id_path_does_not_match_route(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A non-uuid group_id fails the ``<uuid:group_id>`` converter -> Django 404."""
    response = auth_client.delete(_group_url(project.pk, "not-a-uuid"))
    assert response.status_code == 404
