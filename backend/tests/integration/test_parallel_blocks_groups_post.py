"""End-to-end tests for ``POST /api/projects/<pk>/parallel-blocks/groups/``.

Every test drives the real endpoint through the Django test client against a
seeded per-project SQLAlchemy file (``project_db`` fixture). The endpoint opens
its *own* session against the same file, so seeded rows are committed before the
request and the seeding session is expired (``expire_all``) or re-queried fresh
after the request to observe what the endpoint committed.

The confirmed-group save is a full replace: the endpoint validates every entry
against the live candidate components, clears all existing members, then creates
one group per entry, commits, and flips ``Project.has_selected_parallel_sessions``
to ``True``. Any validation failure returns before the commit, so the discarded
``clear_all`` rolls back and prior rows survive.
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
    make_year,
)

WEEK_1 = datetime.date(2025, 9, 15)
WEEK_2 = datetime.date(2025, 9, 22)


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------
def _groups_url(project_id: int) -> str:
    """The confirmed-groups collection URL (always with a trailing slash)."""
    return f"/api/projects/{project_id}/parallel-blocks/groups/"


def _post(client: Client, project_id: int, body: object):
    """POST a JSON body (dict, or already-serialized str) to the groups endpoint."""
    payload = body if isinstance(body, str) else json.dumps(body)
    return client.post(
        _groups_url(project_id),
        data=payload,
        content_type="application/json",
    )


def _entry(candidate_group_id: UUID, block_ids: list[UUID]) -> dict[str, object]:
    """Serialize one save entry to its JSON-ready dict form."""
    return {
        "candidate_group_id": str(candidate_group_id),
        "block_ids": [str(block_id) for block_id in block_ids],
    }


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


# ---------------------------------------------------------------------------
# -- Happy paths
# ---------------------------------------------------------------------------
def test_happy_save_persists_rows_and_flips_flag(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """One valid pair entry: data 1, two rows in one group, flag True."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, b])]})

    assert response.status_code == 200
    assert response.json()["data"] == 1

    groups = _groups_by_id(project_db)
    assert len(groups) == 1
    assert next(iter(groups.values())) == {a, b}
    assert _flag(project.pk) is True


def test_happy_save_visible_to_fresh_reader_via_get(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """After POST, GET /groups/ returns the saved group, proving the commit ran."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    post_response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, b])]})
    assert post_response.status_code == 200

    get_response = auth_client.get(_groups_url(project.pk))
    assert get_response.status_code == 200
    data = get_response.json()["data"]
    assert len(data) == 1
    assert set(map(UUID, data[0]["block_ids"])) == {a, b}


def test_multiple_valid_groups_all_persisted(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two independent pairs: data 2, four rows across two group ids, flag True."""
    # One shared year/degree so the two subjects' auto-created degrees don't
    # collide on the unique acronym; distinct subjects still split components.
    year = make_year(project_db, commit=False)
    subject_1 = make_subject(project_db, year=year, commit=False)
    a, b = make_parallel_candidate_pair(
        project_db,
        subject=subject_1,
        week=WEEK_1,
        start_time=9,
    )
    cid_1 = _component_uuid(subject_1.id, [a, b])

    subject_2 = make_subject(project_db, year=year, commit=False)
    c, d = make_parallel_candidate_pair(
        project_db,
        subject=subject_2,
        week=WEEK_2,
        start_time=10,
    )
    cid_2 = _component_uuid(subject_2.id, [c, d])

    response = _post(
        auth_client,
        project.pk,
        {"groups": [_entry(cid_1, [a, b]), _entry(cid_2, [c, d])]},
    )

    assert response.status_code == 200
    assert response.json()["data"] == 2

    groups = _groups_by_id(project_db)
    assert len(groups) == 2
    assert {frozenset(members) for members in groups.values()} == {
        frozenset({a, b}),
        frozenset({c, d}),
    }
    assert _flag(project.pk) is True


def test_empty_groups_clears_existing_confirmed(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An empty groups list clears every confirmed member; data 0, flag True."""
    group_id = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=y)

    response = _post(auth_client, project.pk, {"groups": []})

    assert response.status_code == 200
    assert response.json()["data"] == 0
    assert _all_members(project_db) == []
    assert _flag(project.pk) is True


def test_empty_groups_on_empty_db(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Empty groups against an already-empty DB: data 0, no rows, flag True."""
    response = _post(auth_client, project.pk, {"groups": []})

    assert response.status_code == 200
    assert response.json()["data"] == 0
    assert _all_members(project_db) == []
    assert _flag(project.pk) is True


# ---------------------------------------------------------------------------
# -- Candidate-validation failures (invalid_candidates, pre-commit rollback)
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

    response = _post(
        auth_client,
        project.pk,
        {"groups": [_entry(uuid.uuid4(), [a, b])]},
    )

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

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, c])]})

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

    response = _post(
        auth_client,
        project.pk,
        {"groups": [_entry(cid, [a, uuid.uuid4()])]},
    )

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

    response = _post(auth_client, project.pk, {"groups": [_entry(stale_cid, [a, b])]})

    assert response.status_code == 400
    assert response.json()["error"] == "projects.parallel_groups.invalid_candidates"
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- create() ValueError failures (invalid_body, transaction rollback)
# ---------------------------------------------------------------------------
def test_duplicate_id_entry_rolls_back_via_create_valueerror(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """[a, a] passes set-based validation but create() rejects <2 distinct blocks."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, a])]})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "generic.invalid_body"
    assert body["message"] == "A parallel block group must contain at least two blocks"

    # clear_all rolled back with the discarded transaction: x, y survive.
    groups = _groups_by_id(project_db)
    assert groups == {seeded_group: {x, y}}
    assert a not in {block for members in groups.values() for block in members}
    assert _flag(project.pk) is False


def test_same_block_across_two_entries_rolls_back_fully(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two entries reusing block a: create() raises 'already belong', full rollback."""
    seeded_group = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=seeded_group, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=seeded_group, original_block_id=y)

    cid, a, b, c = _make_chain_component(project_db, a_b_hub=True)

    response = _post(
        auth_client,
        project.pk,
        {"groups": [_entry(cid, [a, b]), _entry(cid, [a, c])]},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "generic.invalid_body"
    assert body["message"].startswith("Blocks already belong to a confirmed group:")
    assert str(a) in body["message"]

    groups = _groups_by_id(project_db)
    assert groups == {seeded_group: {x, y}}
    assert _flag(project.pk) is False


def test_same_reused_block_different_order_still_rolls_back(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Reusing b across [a,b] then [c,b] still trips the already-grouped guard."""
    cid, a, b, c = _make_chain_component(project_db)

    response = _post(
        auth_client,
        project.pk,
        {"groups": [_entry(cid, [a, b]), _entry(cid, [c, b])]},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "generic.invalid_body"
    assert body["message"].startswith("Blocks already belong to a confirmed group:")
    assert str(b) in body["message"]
    assert _all_members(project_db) == []
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- Entries skipped when too short (never counted, never a 400)
# ---------------------------------------------------------------------------
def test_single_block_entry_skipped_not_counted(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An entry with one block id (garbage cid) is skipped before validation."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(
        auth_client,
        project.pk,
        {
            "groups": [
                _entry(uuid.uuid4(), [a]),  # <2 -> skipped, no 400 despite bad cid
                _entry(cid, [a, b]),
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == 1
    groups = _groups_by_id(project_db)
    assert len(groups) == 1
    assert next(iter(groups.values())) == {a, b}
    assert _flag(project.pk) is True


@pytest.mark.parametrize("empty_block_ids", [[]])
def test_empty_block_ids_entry_skipped(
    auth_client: Client,
    project: Project,
    project_db: Session,
    empty_block_ids: list[str],
) -> None:
    """An entry with an empty block_ids list (garbage cid) is skipped, not a 400."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(
        auth_client,
        project.pk,
        {
            "groups": [
                {"candidate_group_id": str(uuid.uuid4()), "block_ids": empty_block_ids},
                _entry(cid, [a, b]),
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == 1
    groups = _groups_by_id(project_db)
    assert len(groups) == 1
    assert next(iter(groups.values())) == {a, b}


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


@pytest.mark.parametrize(
    ("body", "message_needle"),
    [
        ({"groups": "nope"}, "groups"),
        ({"groups": {}}, "groups"),
        ({}, "groups: Field required"),
    ],
)
def test_wrong_groups_shape_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    body: dict[str, object],
    message_needle: str,
) -> None:
    """``groups`` must be a list; wrong shapes yield 400 invalid_body naming it."""
    response = _post(auth_client, project.pk, body)

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert message_needle in payload["message"]
    assert _all_members(project_db) == []


@pytest.mark.parametrize(
    ("entry", "message_needle"),
    [
        ({"block_ids": [str(uuid.uuid4()), str(uuid.uuid4())]}, "groups.0.candidate_group_id"),
        ({"candidate_group_id": str(uuid.uuid4())}, "groups.0.block_ids"),
    ],
)
def test_entry_missing_required_field_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    entry: dict[str, object],
    message_needle: str,
) -> None:
    """A group entry missing a required field -> 400 invalid_body naming the path."""
    response = _post(auth_client, project.pk, {"groups": [entry]})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert message_needle in payload["message"]
    assert "Field required" in payload["message"]


def test_non_uuid_fields_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Non-UUID candidate_group_id / block id -> 400 invalid_body, no DB write."""
    response = _post(
        auth_client,
        project.pk,
        {"groups": [{"candidate_group_id": "not-a-uuid", "block_ids": ["also-bad"]}]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert "groups.0.candidate_group_id" in payload["message"]
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

    response = _post(Client(), project.pk, {"groups": [_entry(cid, [a, b])]})

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

    response = _post(auth_client, project.pk + 1000, {"groups": [_entry(cid, [a, b])]})

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_unauthenticated_unknown_project_prefers_401(
    project: Project,
    project_db: Session,
) -> None:
    """require_auth runs before require_project: 401 wins over 404."""
    response = _post(Client(), project.pk + 1000, {"groups": []})

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


@pytest.mark.parametrize("method", ["put", "delete"])
def test_wrong_http_method_returns_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """PUT/DELETE on groups/ are undefined on the view -> 405."""
    response = getattr(auth_client, method)(_groups_url(project.pk))
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# -- Scoping, replace semantics, envelope, invariants
# ---------------------------------------------------------------------------
def test_clear_scoped_to_this_project_db(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Clearing touches only the file behind this project's general_db."""
    group_id = uuid.uuid7()
    x, y = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=x, commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=y)

    response = _post(auth_client, project.pk, {"groups": []})

    assert response.status_code == 200
    assert response.json()["data"] == 0
    assert _all_members(project_db) == []


def test_resave_fully_replaces_prior_groups(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A second save with only {c,d} drops the previously saved {a,b}."""
    year = make_year(project_db, commit=False)
    subject_1 = make_subject(project_db, year=year, commit=False)
    a, b = make_parallel_candidate_pair(
        project_db,
        subject=subject_1,
        week=WEEK_1,
        start_time=9,
    )
    cid_1 = _component_uuid(subject_1.id, [a, b])

    subject_2 = make_subject(project_db, year=year, commit=False)
    c, d = make_parallel_candidate_pair(
        project_db,
        subject=subject_2,
        week=WEEK_2,
        start_time=10,
    )
    cid_2 = _component_uuid(subject_2.id, [c, d])

    first = _post(auth_client, project.pk, {"groups": [_entry(cid_1, [a, b])]})
    assert first.status_code == 200
    assert first.json()["data"] == 1

    second = _post(auth_client, project.pk, {"groups": [_entry(cid_2, [c, d])]})
    assert second.status_code == 200
    assert second.json()["data"] == 1

    groups = _groups_by_id(project_db)
    assert len(groups) == 1
    assert next(iter(groups.values())) == {c, d}
    assert _flag(project.pk) is True


def test_error_path_leaves_flag_unchanged_when_already_true(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A pre-set True flag stays True across a failing (400) save."""
    Project.objects.filter(pk=project.pk).update(has_selected_parallel_sessions=True)

    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, a])]})

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _flag(project.pk) is True


def test_success_envelope_shape_and_json_types(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Success envelope has {timestamp, message, data}; data is a JSON number."""
    subject = make_subject(project_db, commit=False)
    a, b = make_parallel_candidate_pair(project_db, subject=subject)
    cid = _component_uuid(subject.id, [a, b])

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, b])]})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert payload["data"] == 1
    assert isinstance(payload["data"], int)
    assert not isinstance(payload["data"], bool)
    assert isinstance(payload["message"], str) and payload["message"]
    # ISO-8601 timestamp: parseable, not asserted on its volatile value.
    datetime.datetime.fromisoformat(payload["timestamp"])


def test_valid_save_of_connected_proper_subset(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A connected 2-block subset of a 3-block component saves as exactly {a,b}."""
    cid, a, b, _c = _make_chain_component(project_db)

    response = _post(auth_client, project.pk, {"groups": [_entry(cid, [a, b])]})

    assert response.status_code == 200
    assert response.json()["data"] == 1
    groups = _groups_by_id(project_db)
    assert len(groups) == 1
    assert next(iter(groups.values())) == {a, b}
    assert _flag(project.pk) is True
