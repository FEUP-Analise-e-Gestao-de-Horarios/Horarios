"""End-to-end tests for ``POST /api/projects/<pk>/parallel-blocks/groups/``.

Every test drives the real endpoint through the Django test client against a
seeded per-project SQLAlchemy file (``project_db`` fixture). The endpoint opens
its *own* session against the same file, so seeded rows are committed before the
request and the seeding session is expired (``expire_all``) or re-queried fresh
after the request to observe what the endpoint committed.

The confirmed-group create is *additive*: the endpoint validates one entry
against the live candidate components, creates a single fresh group from its
blocks, commits, and flips ``Project.has_selected_parallel_sessions`` to
``True``. It never clears pre-existing groups -- a POST adds a new group
alongside any others. Any validation failure returns before the commit, so no
rows are written and prior groups survive untouched.
"""

import datetime
import json
import uuid
from uuid import UUID

import pytest
from django.test import Client
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.dao.parallel_candidate_graph import _component_uuid
from src.projects.projects_db.models import ParallelBlockGroupMember
from tests.factories import (
    make_class,
    make_group_member,
    make_parallel_candidate_pair,
    make_session,
    make_session_class_subject,
    make_subject,
)

WEEK_1 = datetime.date(2025, 9, 15)
WEEK_2 = datetime.date(2025, 9, 22)
WEEK_3 = datetime.date(2025, 9, 29)


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------
def _groups_url(project_id: int) -> str:
    """The confirmed-groups collection URL (always with a trailing slash)."""
    return f"/api/projects/{project_id}/parallel-blocks/groups/"


def _body(candidate_group_id: UUID, block_ids: list[UUID]) -> dict[str, object]:
    """Serialize the single create-one request body to its JSON-ready dict form."""
    return {
        "candidate_group_id": str(candidate_group_id),
        "block_ids": [str(block_id) for block_id in block_ids],
    }


def _post(client: Client, project_id: int, body: object):
    """POST a JSON body (dict, or already-serialized str) to the groups endpoint."""
    payload = body if isinstance(body, str) else json.dumps(body)
    return client.post(
        _groups_url(project_id),
        data=payload,
        content_type="application/json",
    )


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


def _make_chain_component(
    db_session: Session,
    *,
    a_b_hub: bool = False,
) -> tuple[UUID, UUID, UUID, UUID]:
    """Seed a 3-block connected component of one subject and return its ids.

    All sessions share the same ``(weekday, start_time)`` (only the week
    varies) so every block stays eligible for candidate detection.

    * Default chain: ``a`` & ``b`` collide on ``WEEK_1``, ``b`` & ``c`` collide
      on ``WEEK_2`` (``b`` is the middle node; there is no ``a``-``c`` edge).
    * ``a_b_hub=True``: ``a`` & ``b`` on ``WEEK_1``, ``a`` & ``c`` on ``WEEK_2``
      (``a`` is the hub shared across both slots).

    Returns ``(cid, a, b, c)`` where ``cid`` is the component's
    ``_component_uuid`` over the sorted three members.
    """
    subject = make_subject(db_session, commit=False)
    year = subject.years[0]
    class_a = make_class(db_session, year=year, commit=False)
    class_b = make_class(db_session, year=year, commit=False)
    class_c = make_class(db_session, year=year, commit=False)

    a = uuid.uuid7()
    b = uuid.uuid7()
    c = uuid.uuid7()

    def _seat(block_id: UUID, week: datetime.date, class_row: object) -> None:
        session_row = make_session(
            db_session,
            week=week,
            start_time=9,
            original_block_id=block_id,
            commit=False,
        )
        make_session_class_subject(
            db_session,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
            commit=False,
        )

    if a_b_hub:
        # a is the hub: {a, b} on WEEK_1 and {a, c} on WEEK_2.
        _seat(a, WEEK_1, class_a)
        _seat(b, WEEK_1, class_b)
        _seat(a, WEEK_2, class_a)
        _seat(c, WEEK_2, class_c)
    else:
        # chain: {a, b} on WEEK_1 and {b, c} on WEEK_2.
        _seat(a, WEEK_1, class_a)
        _seat(b, WEEK_1, class_b)
        _seat(b, WEEK_2, class_b)
        _seat(c, WEEK_2, class_c)

    db_session.commit()
    cid = _component_uuid(subject.id, [a, b, c])
    return cid, a, b, c


def _group_id_from(response) -> UUID:
    """Extract and parse the ``group_id`` from a successful create response."""
    return UUID(response.json()["data"]["group_id"])


# ---------------------------------------------------------------------------
# -- Happy paths
# ---------------------------------------------------------------------------
def test_happy_create_persists_rows_and_flips_flag(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """One valid pair: data.group_id is a uuid, two rows in one group, flag True."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, b]))

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, dict)
    group_id = UUID(data["group_id"])  # parses as a uuid string

    groups = _groups_by_id(project_db)
    assert groups == {group_id: {a, b}}
    assert _flag(project.pk) is True


def test_happy_create_visible_to_fresh_reader_via_get(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """After POST, GET /groups/ returns the saved group, proving the commit ran."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    post_response = _post(auth_client, project.pk, _body(cid, [a, b]))
    assert post_response.status_code == 200
    group_id = _group_id_from(post_response)

    get_response = auth_client.get(_groups_url(project.pk))
    assert get_response.status_code == 200
    data = get_response.json()["data"]
    assert len(data) == 1
    assert data[0]["group_id"] == str(group_id)
    assert set(map(UUID, data[0]["block_ids"])) == {a, b}


def test_post_is_additive_existing_group_survives(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A new POST adds a group alongside a pre-seeded one; both survive."""
    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, b]))

    assert response.status_code == 200
    new_group = _group_id_from(response)
    assert new_group != seeded_group

    groups = _groups_by_id(project_db)
    assert groups == {seeded_group: {x, y}, new_group: {a, b}}
    assert _flag(project.pk) is True


def test_valid_create_of_connected_proper_subset(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A connected 2-block subset of a 3-block component saves as exactly {a,b}."""
    cid, a, b, _c = _make_chain_component(project_db)

    response = _post(auth_client, project.pk, _body(cid, [a, b]))

    assert response.status_code == 200
    group_id = _group_id_from(response)
    assert _groups_by_id(project_db) == {group_id: {a, b}}
    assert _flag(project.pk) is True


def test_two_disjoint_subsets_via_two_posts_make_two_groups(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two successive POSTs of disjoint connected subsets of one component -> two groups.

    The chain a-b-c-d (edges a-b, b-c, c-d) is a single component, but {a, b}
    and {c, d} are each a connected subset sharing no block. Confirming {a, b}
    first does not change candidate detection (which reads only sessions), so a
    second POST of {c, d} against the same candidate id also validates.
    """
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    classes = [make_class(project_db, year=year, commit=False) for _ in range(4)]
    a, b, c, d = (uuid.uuid7() for _ in range(4))

    def _seat(block_id: UUID, week: datetime.date, class_row: object) -> None:
        session_row = make_session(
            project_db,
            week=week,
            start_time=9,
            original_block_id=block_id,
            commit=False,
        )
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
            commit=False,
        )

    _seat(a, WEEK_1, classes[0])
    _seat(b, WEEK_1, classes[1])
    _seat(b, WEEK_2, classes[1])
    _seat(c, WEEK_2, classes[2])
    _seat(c, WEEK_3, classes[2])
    _seat(d, WEEK_3, classes[3])
    project_db.commit()

    cid = _component_uuid(subject.id, [a, b, c, d])

    first = _post(auth_client, project.pk, _body(cid, [a, b]))
    assert first.status_code == 200
    group_ab = _group_id_from(first)

    second = _post(auth_client, project.pk, _body(cid, [c, d]))
    assert second.status_code == 200
    group_cd = _group_id_from(second)

    assert group_ab != group_cd
    assert _groups_by_id(project_db) == {group_ab: {a, b}, group_cd: {c, d}}
    assert _flag(project.pk) is True


def test_duplicate_block_within_body_is_deduped_not_500(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """``block_ids=[a, b, a]`` (set of 2) passes validation and dedups in create.

    The duplicate collapses via ``dict.fromkeys`` inside ``create`` rather than
    hitting the UNIQUE constraint, so it saves a single {a, b} group instead of
    surfacing an IntegrityError as a 500.
    """
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, b, a]))

    assert response.status_code == 200
    group_id = _group_id_from(response)
    assert _groups_by_id(project_db) == {group_id: {a, b}}
    assert _flag(project.pk) is True


# ---------------------------------------------------------------------------
# -- Candidate-validation failures (invalid_candidates, nothing written)
# ---------------------------------------------------------------------------
def test_unknown_candidate_group_id_rejected_and_existing_intact(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A candidate_group_id matching no component -> 400, existing rows intact."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)

    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    response = _post(auth_client, project.pk, _body(uuid.uuid4(), [a, b]))

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "projects.parallel_groups.invalid_candidates"
    assert body["message"] == "Some classes are not parallel candidates."

    groups = _groups_by_id(project_db)
    assert groups == {seeded_group: {x, y}}
    assert a not in {block for members in groups.values() for block in members}
    assert _flag(project.pk) is False


def test_non_connected_subset_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Selecting the two endpoints of a chain (no direct edge) -> 400."""
    cid, a, _b, c = _make_chain_component(project_db)

    response = _post(auth_client, project.pk, _body(cid, [a, c]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


def test_subset_with_foreign_block_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A subset containing a block absent from the component -> 400."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, uuid.uuid4()]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


def test_stale_candidate_group_id_after_membership_change_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A cid computed for {a,b} is stale once a third block joins the slot."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    a, b = make_parallel_candidate_pair(
        project_db,
        subject=subject,
        week=WEEK_1,
        start_time=9,
        commit=False,
    )
    stale_cid = _component_uuid(subject.id, [a, b])

    # A third block c joins the same slot, so the live component is {a, b, c}
    # whose id differs from stale_cid over just {a, b}.
    class_c = make_class(project_db, year=year, commit=False)
    c = uuid.uuid7()
    session_c = make_session(
        project_db,
        week=WEEK_1,
        start_time=9,
        original_block_id=c,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_c,
        class_row=class_c,
        subject=subject,
        commit=False,
    )
    project_db.commit()

    live_cid = _component_uuid(subject.id, [a, b, c])
    assert stale_cid != live_cid

    response = _post(auth_client, project.pk, _body(stale_cid, [a, b]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


def test_duplicate_id_list_set_size_one_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """``[a, a]`` collapses to a set of size 1 -> invalid_candidates 400 (not skipped)."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    response = _post(auth_client, project.pk, _body(cid, [a, a]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _groups_by_id(project_db) == {seeded_group: {x, y}}
    assert _flag(project.pk) is False


def test_single_block_list_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A single-block ``block_ids=[a]`` -> set size 1 -> invalid_candidates 400."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


def test_empty_block_ids_list_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An empty ``block_ids=[]`` -> set size 0 -> invalid_candidates 400, nothing written."""
    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    response = _post(auth_client, project.pk, _body(uuid.uuid4(), []))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _groups_by_id(project_db) == {seeded_group: {x, y}}
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- create() ValueError failure (invalid_body, block already grouped)
# ---------------------------------------------------------------------------
def test_reused_block_already_in_confirmed_group_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A valid pair whose block already belongs to a confirmed group -> 400 invalid_body."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject, commit=False)
    cid = _component_uuid(subject.id, [a, b])

    # Seed a confirmed group that already owns block a.
    seeded_group = uuid.uuid7()
    z = uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=a, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=z)

    response = _post(auth_client, project.pk, _body(cid, [a, b]))

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "generic.invalid_body"
    assert body["message"].startswith("Blocks already belong to a confirmed group:")
    assert str(a) in body["message"]

    # The pre-existing group is untouched; b was never written.
    groups = _groups_by_id(project_db)
    assert groups == {seeded_group: {a, z}}
    assert b not in {block for members in groups.values() for block in members}
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- Body validation failures (validate_request_body / pydantic)
# ---------------------------------------------------------------------------
def test_invalid_json_body_rejected_before_db(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Malformed JSON -> 400 invalid_body before the session opens; no mutation."""
    response = _post(auth_client, project.pk, "{not valid json")

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "generic.invalid_body"
    assert body["message"]
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


@pytest.mark.parametrize("body", [[], 5])
def test_non_object_json_body_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    body: object,
) -> None:
    """A syntactically valid but non-object top-level body -> 400 invalid_body, no mutation."""
    response = _post(auth_client, project.pk, body)

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert payload["message"] == "Input should be an object"
    assert _all_members(project_db) == []


def test_missing_candidate_group_id_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Omitting ``candidate_group_id`` -> 400 invalid_body naming the field."""
    response = _post(
        auth_client,
        project.pk,
        {"block_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert "candidate_group_id" in payload["message"]
    assert "Field required" in payload["message"]
    assert _all_members(project_db) == []


def test_missing_block_ids_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Omitting ``block_ids`` -> 400 invalid_body naming the field."""
    response = _post(
        auth_client,
        project.pk,
        {"candidate_group_id": str(uuid.uuid4())},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert "block_ids" in payload["message"]
    assert "Field required" in payload["message"]
    assert _all_members(project_db) == []


def test_non_uuid_fields_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Non-UUID candidate_group_id / block id -> 400 invalid_body, no DB write."""
    response = _post(
        auth_client,
        project.pk,
        {"candidate_group_id": "not-a-uuid", "block_ids": ["also-bad"]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert "candidate_group_id" in payload["message"]
    assert _all_members(project_db) == []


# ---------------------------------------------------------------------------
# -- Decorators (auth / project) and dispatch
# ---------------------------------------------------------------------------
def test_unauthenticated_post_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """A fresh unauthenticated client -> 401 before any body parse or DB access."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(Client(), project.pk, _body(cid, [a, b]))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


def test_unknown_project_post_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A valid body posted to a nonexistent project id -> 404 from require_project."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk + 1000, _body(cid, [a, b]))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_unauthenticated_unknown_project_prefers_401(
    project: Project,
    project_db: Session,
) -> None:
    """require_auth runs before require_project: 401 wins over 404."""
    response = _post(Client(), project.pk + 1000, _body(uuid.uuid4(), [uuid.uuid7(), uuid.uuid7()]))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_wrong_http_method_returns_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """PUT is undefined on the collection view -> 405 (DELETE is now a valid verb)."""
    response = auth_client.put(_groups_url(project.pk))
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# -- Envelope, invariants
# ---------------------------------------------------------------------------
def test_success_envelope_shape_and_json_types(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Success envelope has {timestamp, message, data}; data is a {group_id} dict."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, b]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert isinstance(payload["data"], dict)
    assert set(payload["data"]) == {"group_id"}
    assert isinstance(payload["data"]["group_id"], str)
    UUID(payload["data"]["group_id"])  # parses as a uuid
    assert isinstance(payload["message"], str) and payload["message"]
    # ISO-8601 timestamp: parseable, not asserted on its volatile value.
    datetime.datetime.fromisoformat(payload["timestamp"])


def test_error_path_leaves_flag_unchanged_when_already_true(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A pre-set True flag stays True across a failing (400) POST."""
    Project.objects.filter(pk=project.pk).update(has_selected_parallel_sessions=True)

    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, _body(cid, [a, a]))

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _flag(project.pk) is True
