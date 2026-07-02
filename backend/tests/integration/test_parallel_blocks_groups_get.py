"""Integration tests for ``GET /api/projects/<pk>/parallel-blocks/groups/``.

Every case drives the real endpoint through the Django test client against a
seeded, per-project SQLite file (the ``project_db`` fixture). This file owns the
GET verb of ``ProjectParallelBlockGroupsView`` end to end: auth/project
decorator ordering, the trailing-slash route, method dispatch, and the wire
shape produced by ``ParallelBlockGroupDAO.get_all_groups`` +
``ParallelGroupResponse``.

Seeding uses ``make_group_member`` (which commits) so the endpoint's own
session sees the rows. Because there is no ``ORDER BY`` anywhere in the read
path, assertions compare *sets* of block ids and a ``{group_id: set}`` mapping,
never positional order. The volatile ``timestamp`` field is only checked for
presence/parseability, never for value.
"""

import datetime
import json
import uuid
from collections.abc import Iterator
from uuid import UUID

import pytest
from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.dao.parallel_candidate_graph import _component_uuid
from src.projects.projects_db.paths import general_db, project_dir
from src.projects.projects_db.registry import evict_engine, init_engine
from src.projects.views.schemas.parallel_blocks import ParallelGroupResponse
from tests.factories import make_group_member, make_parallel_candidate_pair

GROUP_MESSAGE = "Parallel group members retrieved successfully"


def _groups_url(project_id: int) -> str:
    """The trailing slash is required: ``groups/`` is the routed pattern."""
    return f"/api/projects/{project_id}/parallel-blocks/groups/"


def _candidates_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/candidates"


def _groups_by_id(payload_data: list[dict]) -> dict[str, set[str]]:
    """Map each returned entry's ``group_id`` to the set of its ``block_ids``."""
    return {entry["group_id"]: set(entry["block_ids"]) for entry in payload_data}


# ---------------------------------------------------------------------------
# -- Auth / project decorators (GET verb)
# ---------------------------------------------------------------------------


def test_unauthenticated_get_returns_401(project: Project, project_db: Session) -> None:
    """No login -> 401 from ``require_auth`` before any project-DB access."""
    response = Client().get(_groups_url(project.pk))

    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "auth.not_authenticated"
    assert body["message"] == "User is not authenticated."


def test_unauthenticated_get_unknown_project_still_401(project: Project) -> None:
    """Auth is checked before the project lookup: 401 wins over 404."""
    response = Client().get(_groups_url(project.pk + 1000))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_authenticated_get_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
) -> None:
    """A logged-in request for a missing project id is rejected by ``require_project``."""
    response = auth_client.get(_groups_url(project.pk + 1000))

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "projects.not_found"
    assert body["message"] == "Project not found."


# ---------------------------------------------------------------------------
# -- Read path: get_all_groups -> ParallelGroupResponse
# ---------------------------------------------------------------------------


def test_empty_db_returns_empty_data(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """No membership rows -> ``data == []`` with the confirmed-groups message."""
    response = auth_client.get(_groups_url(project.pk))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["message"] == GROUP_MESSAGE
    # timestamp present and ISO-parseable, but its value is volatile.
    assert datetime.datetime.fromisoformat(payload["timestamp"])


def test_single_group_two_members(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """One group with two members -> one entry carrying both block ids."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b)

    response = auth_client.get(_groups_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    entry = data[0]
    assert entry["group_id"] == str(group_id)
    assert set(entry["block_ids"]) == {str(block_a), str(block_b)}
    assert len(entry["block_ids"]) == 2


def test_two_distinct_groups_bucketed_correctly(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two groups (sizes 2 and 3), interleaved on insert, stay uncontaminated."""
    g1, g2 = uuid.uuid7(), uuid.uuid7()
    a1, a2 = uuid.uuid7(), uuid.uuid7()
    b1, b2, b3 = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()

    # Interleave inserts so a naive grouping bug would smear members together.
    make_group_member(project_db, group_id=g1, original_block_id=a1)
    make_group_member(project_db, group_id=g2, original_block_id=b1)
    make_group_member(project_db, group_id=g1, original_block_id=a2)
    make_group_member(project_db, group_id=g2, original_block_id=b2)
    make_group_member(project_db, group_id=g2, original_block_id=b3)

    response = auth_client.get(_groups_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert _groups_by_id(data) == {
        str(g1): {str(a1), str(a2)},
        str(g2): {str(b1), str(b2), str(b3)},
    }


@pytest.mark.parametrize("member_count", [1, 2, 3, 6])
def test_group_returned_regardless_of_size(
    auth_client: Client,
    project: Project,
    project_db: Session,
    member_count: int,
) -> None:
    """GET applies no min-size filter: even a singleton group is returned verbatim."""
    group_id = uuid.uuid7()
    block_ids = [uuid.uuid7() for _ in range(member_count)]
    for block_id in block_ids:
        make_group_member(project_db, group_id=group_id, original_block_id=block_id)

    response = auth_client.get(_groups_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    entry = data[0]
    assert entry["group_id"] == str(group_id)
    assert set(entry["block_ids"]) == {str(b) for b in block_ids}
    assert len(entry["block_ids"]) == member_count


def test_response_ids_are_json_strings(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """UUIDs serialize as strings and round-trip through ``UUID(...)``."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b)

    payload = auth_client.get(_groups_url(project.pk)).json()
    entry = payload["data"][0]

    assert isinstance(entry["group_id"], str)
    assert UUID(entry["group_id"]) == group_id
    for block_id in entry["block_ids"]:
        assert isinstance(block_id, str)
        assert UUID(block_id) in {block_a, block_b}
    # timestamp is a string too, parseable as ISO 8601.
    assert isinstance(payload["timestamp"], str)
    assert datetime.datetime.fromisoformat(payload["timestamp"])


def test_response_entries_match_schema_no_extra_fields(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Each entry has exactly ``group_id``/``block_ids`` and validates against the schema."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b)

    entry = auth_client.get(_groups_url(project.pk)).json()["data"][0]

    assert set(entry.keys()) == {"group_id", "block_ids"}
    # No candidate-only fields (subject/nodes/edges/candidate_group_id) leak in.
    for leaked in ("candidate_group_id", "subject", "nodes", "edges", "weekday"):
        assert leaked not in entry

    model = ParallelGroupResponse.model_validate(entry)
    assert model.group_id == group_id
    assert set(model.block_ids) == {block_a, block_b}


# ---------------------------------------------------------------------------
# -- Interaction with the POST write path
# ---------------------------------------------------------------------------


def test_get_reflects_prior_post_round_trip(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A POSTed group becomes visible on the next GET with a fresh group id."""
    block_a, block_b = make_parallel_candidate_pair(project_db)

    # Discover the candidate group id the save endpoint expects.
    candidates = auth_client.get(_candidates_url(project.pk)).json()["data"]
    assert len(candidates) == 1
    candidate_group_id = candidates[0]["candidate_group_id"]
    # Sanity: the deterministic component id matches ``_component_uuid``.
    subject_id = UUID(candidates[0]["subject"]["id"])
    assert candidate_group_id == str(_component_uuid(subject_id, [block_a, block_b]))

    post = auth_client.post(
        _groups_url(project.pk),
        data=json.dumps(
            {
                "groups": [
                    {
                        "candidate_group_id": candidate_group_id,
                        "block_ids": [str(block_a), str(block_b)],
                    },
                ],
            },
        ),
        content_type="application/json",
    )
    assert post.status_code == 200
    assert post.json()["data"] == 1

    data = auth_client.get(_groups_url(project.pk)).json()["data"]
    assert len(data) == 1
    entry = data[0]
    assert set(entry["block_ids"]) == {str(block_a), str(block_b)}
    # A confirmed group id is freshly generated, not the candidate id.
    assert UUID(entry["group_id"])
    assert entry["group_id"] != candidate_group_id


def test_get_after_post_clears_all_returns_empty(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """POST with an empty group list clears everything; the next GET sees nothing."""
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=uuid.uuid7())
    make_group_member(project_db, group_id=group_id, original_block_id=uuid.uuid7())

    post = auth_client.post(
        _groups_url(project.pk),
        data=json.dumps({"groups": []}),
        content_type="application/json",
    )
    assert post.status_code == 200
    assert post.json()["data"] == 0

    response = auth_client.get(_groups_url(project.pk))
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_get_unaffected_by_rejected_post(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An invalid-candidates POST is rejected before ``clear_all``; prior groups survive."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b)

    # An unknown candidate_group_id with two distinct blocks -> 400, no mutation.
    post = auth_client.post(
        _groups_url(project.pk),
        data=json.dumps(
            {
                "groups": [
                    {
                        "candidate_group_id": str(uuid.uuid7()),
                        "block_ids": [str(uuid.uuid7()), str(uuid.uuid7())],
                    },
                ],
            },
        ),
        content_type="application/json",
    )
    assert post.status_code == 400
    assert post.json()["error"] == "projects.parallel_groups.invalid_candidates"

    data = auth_client.get(_groups_url(project.pk)).json()["data"]
    assert len(data) == 1
    entry = data[0]
    assert entry["group_id"] == str(group_id)
    assert set(entry["block_ids"]) == {str(block_a), str(block_b)}


# ---------------------------------------------------------------------------
# -- Cross-project isolation
# ---------------------------------------------------------------------------


@pytest.fixture
def project_b(project: Project, settings, tmp_path) -> Iterator[Project]:
    """A second project with its own empty per-project DB under the shared tmp path.

    ``project`` (via ``project_db``) already points ``PROJECTS_DB_PATH`` at
    ``tmp_path``; this fixture provisions a distinct project row plus its own
    ``general_database.db`` beneath the same root and evicts the engine on
    teardown so the module-global cache does not leak across tests.
    """
    settings.PROJECTS_DB_PATH = tmp_path
    other = Project.objects.create(
        name="Second Project",
        url="https://example.com/other-schedule",
        creator=project.creator,
    )
    db_path = general_db(other.pk)
    project_dir(other.pk).mkdir(parents=True, exist_ok=True)
    init_engine(db_path)
    try:
        yield other
    finally:
        evict_engine(db_path)


def test_cross_project_isolation(
    auth_client: Client,
    project: Project,
    project_db: Session,
    project_b: Project,
) -> None:
    """Project A is seeded; GET on empty project B sees none of A's groups."""
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=uuid.uuid7())
    make_group_member(project_db, group_id=group_id, original_block_id=uuid.uuid7())

    # A has one group.
    a_data = auth_client.get(_groups_url(project.pk)).json()["data"]
    assert len(a_data) == 1

    # B's own DB is empty.
    response = auth_client.get(_groups_url(project_b.pk))
    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# -- Method dispatch & trailing-slash routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["put", "delete"])
def test_unsupported_methods_return_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """The view defines only get/post; PUT and DELETE fall through to 405."""
    response = getattr(auth_client, method)(_groups_url(project.pk))
    assert response.status_code == 405


def test_missing_trailing_slash_redirects(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """APPEND_SLASH redirects ``/groups`` (301) to ``/groups/``; following it -> 200."""
    no_slash = f"/api/projects/{project.pk}/parallel-blocks/groups"

    redirect = auth_client.get(no_slash)
    assert redirect.status_code == 301
    assert redirect["Location"].endswith(_groups_url(project.pk))

    followed = auth_client.get(no_slash, follow=True)
    assert followed.status_code == 200
    assert followed.json()["data"] == []
