"""End-to-end tests for the parallel-blocks *confirmation* endpoints.

Covered routes (all under ``/api/projects/<pk>/parallel-blocks/confirmations``):

* ``POST  /``            -- confirm one subject's current candidates
* ``POST  /all``         -- confirm every current candidate
* ``DELETE /<subject_id>`` -- drop one subject's confirmation
* ``DELETE /``           -- clear every confirmation

plus the ``confirmed`` flag now surfaced on each subject by the candidates GET,
and the read-time reconciliation that prunes stale/partial confirmations.

Each test drives the real endpoint through the Django test client against a
seeded per-project SQLite file (``project_db``). The endpoint opens its own
session, so seeded rows are committed first and the seeding session is expired /
re-queried to observe what the endpoint committed.
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
from src.projects.projects_db.models import (
    ParallelBlockGroupMember,
    ParallelConfirmedCandidate,
    Subject,
)
from tests.factories import (
    make_class,
    make_confirmed_candidate,
    make_degree,
    make_group_member,
    make_parallel_candidate_pair,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)

WEEK = datetime.date(2025, 9, 15)

_ACRONYM_POOL = iter(f"C{n:03d}" for n in range(1000))


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------
def _candidates_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/candidates"


def _confirmations_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/confirmations/"


def _confirmation_url(project_id: int, subject_id: UUID) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/confirmations/{subject_id}"


def _confirm_all_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/confirmations/all"


def _post(client: Client, url: str, body: object | None = None):
    return client.post(url, data=json.dumps(body or {}), content_type="application/json")


def _post_raw(client: Client, url: str, raw: str):
    """POST an already-serialized (possibly falsy or malformed) JSON body verbatim."""
    return client.post(url, data=raw, content_type="application/json")


def _confirm_body(subject_id: UUID, candidate_group_ids: list[UUID]) -> dict[str, object]:
    """Body for the confirm-subject endpoint, with the client's candidate view."""
    return {
        "subject_id": str(subject_id),
        "candidate_group_ids": [str(cid) for cid in candidate_group_ids],
    }


def _confirm_all_body(candidate_group_ids: list[UUID]) -> dict[str, object]:
    """Body for the confirm-all endpoint, with the client's full candidate view."""
    return {"candidate_group_ids": [str(cid) for cid in candidate_group_ids]}


def _stored(db_session: Session) -> set[UUID]:
    db_session.expire_all()
    return set(db_session.scalars(select(ParallelConfirmedCandidate.candidate_group_id)).all())


def _confirmed_by_subject(client: Client, project_id: int) -> dict[str, bool]:
    """subject id -> its ``confirmed`` flag from the candidates GET."""
    payload = client.get(_candidates_url(project_id)).json()
    return {g["subject"]["id"]: g["subject"]["confirmed"] for g in payload["data"]}


def _make_subject_with_degree(session: Session):
    degree = make_degree(session, acronym=next(_ACRONYM_POOL), commit=False)
    year = make_year(session, degree=degree, commit=False)
    return make_subject(session, year=year, commit=False)


def _add_block_to_subject_slot(session: Session, subject: Subject, *, start_time: int = 9) -> UUID:
    """Attach one more block to a subject's existing candidate slot; return its id.

    The new block shares the pair's default ``(week, weekday, start_time)`` slot,
    so all blocks in that slot collapse into a single, larger component whose
    ``candidate_group_id`` differs from the smaller one stored before.
    """
    year = subject.years[0]
    class_row = make_class(session, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        session,
        start_time=start_time,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        session,
        session_row=session_row,
        class_row=class_row,
        subject=subject,
    )
    return block_id


def _flag(project_id: int) -> bool:
    """Reload the Django ``Project`` and return its parallel-selection flag."""
    return Project.objects.get(pk=project_id).has_selected_parallel_sessions


def _group_members(db_session: Session) -> set[tuple[UUID, UUID]]:
    """Every confirmed-group membership as ``(group_id, original_block_id)`` pairs."""
    db_session.expire_all()
    return {
        (row.parallel_block_group_id, row.original_block_id)
        for row in db_session.scalars(select(ParallelBlockGroupMember)).all()
    }


# ---------------------------------------------------------------------------
# -- Candidates GET: confirmed flag
# ---------------------------------------------------------------------------


def test_candidates_confirmed_flag_defaults_false(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """With nothing stored, every subject reports confirmed=False."""
    make_parallel_candidate_pair(project_db)

    assert set(_confirmed_by_subject(auth_client, project.pk).values()) == {False}


def test_confirm_subject_sets_flag_true(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming a subject stores its candidate and flips its GET flag."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)
    candidate_id = _component_uuid(subject.id, [block_a, block_b])

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [candidate_id]),
    )

    assert response.status_code == 200
    assert response.json()["data"]["candidate_group_ids"] == [str(candidate_id)]
    assert _stored(project_db) == {candidate_id}
    assert _confirmed_by_subject(auth_client, project.pk)[str(subject.id)] is True


def test_confirm_subject_requires_all_components(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A subject with two components is confirmed only once both are stored."""
    subject = make_subject(project_db, commit=False)
    # Two components of the same subject: two disjoint slots (9h and 14h).
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=9)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=14)
    comp_a = _component_uuid(subject.id, [a1, a2])
    comp_b = _component_uuid(subject.id, [b1, b2])

    # Seed only one of the two components as confirmed: the GET must report the
    # subject unconfirmed and prune the partial id.
    make_confirmed_candidate(project_db, candidate_group_id=comp_a)
    assert _confirmed_by_subject(auth_client, project.pk)[str(subject.id)] is False
    assert _stored(project_db) == set()

    # Confirming via the endpoint stores *both* components -> confirmed.
    _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [comp_a, comp_b]))
    assert _stored(project_db) == {comp_a, comp_b}
    assert _confirmed_by_subject(auth_client, project.pk)[str(subject.id)] is True


def test_confirm_all_confirms_every_subject(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """POST /all stores every current candidate across subjects."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject_b)
    comp_a = _component_uuid(subject_a.id, [a1, a2])
    comp_b = _component_uuid(subject_b.id, [b1, b2])

    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp_a, comp_b]))

    assert response.status_code == 200
    assert _stored(project_db) == {comp_a, comp_b}
    flags = _confirmed_by_subject(auth_client, project.pk)
    assert flags == {str(subject_a.id): True, str(subject_b.id): True}


def test_unconfirm_subject_clears_only_that_subject(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE /<subject_id> removes one subject's confirmation, leaving others."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject_b)
    comp_a = _component_uuid(subject_a.id, [a1, a2])
    comp_b = _component_uuid(subject_b.id, [b1, b2])
    _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp_a, comp_b]))

    response = auth_client.delete(_confirmation_url(project.pk, subject_a.id))

    assert response.status_code == 200
    assert _stored(project_db) == {comp_b}
    flags = _confirmed_by_subject(auth_client, project.pk)
    assert flags == {str(subject_a.id): False, str(subject_b.id): True}


def test_clear_all_confirmations(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE / drops every confirmation."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)
    candidate_id = _component_uuid(subject.id, [block_a, block_b])
    _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [candidate_id]))
    assert _stored(project_db) != set()

    response = auth_client.delete(_confirmations_url(project.pk))

    assert response.status_code == 200
    assert _stored(project_db) == set()
    assert _confirmed_by_subject(auth_client, project.pk)[str(subject.id)] is False


def test_get_prunes_orphan_confirmation(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A stored id matching no current candidate is pruned on the next GET."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)
    candidate_id = _component_uuid(subject.id, [block_a, block_b])
    orphan = uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=candidate_id)
    make_confirmed_candidate(project_db, candidate_group_id=orphan)

    flags = _confirmed_by_subject(auth_client, project.pk)

    assert flags[str(subject.id)] is True
    # The orphan is gone; only the live, fully-confirmed id survives.
    assert _stored(project_db) == {candidate_id}


def test_confirm_unknown_subject_stores_nothing(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming a subject with no candidates (empty client view) is a no-op."""
    make_parallel_candidate_pair(project_db)

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(uuid.uuid7(), []),
    )

    assert response.status_code == 200
    assert response.json()["data"]["candidate_group_ids"] == []
    assert _stored(project_db) == set()


def test_confirm_stale_candidate_view_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A confirm naming candidate ids that don't match the live set is rejected 409."""
    subject = make_subject(project_db, commit=False)
    make_parallel_candidate_pair(project_db, subject=subject)

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [uuid.uuid7()]),
    )

    assert response.status_code == 409
    assert response.json()["error"] == "projects.parallel_confirmation.stale"
    assert _stored(project_db) == set()


def test_confirm_partial_candidate_view_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming with only some of a subject's live candidates is rejected 409."""
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=9)
    make_parallel_candidate_pair(project_db, subject=subject, start_time=14)
    comp_a = _component_uuid(subject.id, [a1, a2])  # only one of the two components

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [comp_a]),
    )

    assert response.status_code == 409
    assert _stored(project_db) == set()


def test_confirm_all_stale_candidate_view_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all with a candidate set that doesn't match the live one is rejected 409."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    make_parallel_candidate_pair(project_db, subject=subject_b)
    comp_a = _component_uuid(subject_a.id, [a1, a2])

    # The client only knows about subject_a's candidate -> stale view.
    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp_a]))

    assert response.status_code == 409
    assert response.json()["error"] == "projects.parallel_confirmation.stale"
    assert _stored(project_db) == set()


def test_confirm_invalid_body_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A body missing subject_id is rejected before any write."""
    response = _post(auth_client, _confirmations_url(project.pk), {})

    assert response.status_code == 400
    assert _stored(project_db) == set()


def test_confirmations_unauthenticated_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """A fresh client is rejected 401 on the confirm endpoint; nothing stored."""
    stored = uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=stored)

    response = _post(Client(), _confirmations_url(project.pk), {"subject_id": str(uuid.uuid7())})

    assert response.status_code == 401
    assert _stored(project_db) == {stored}


# ---------------------------------------------------------------------------
# -- Confirm-all: invalid body, empty candidate set, envelope
# ---------------------------------------------------------------------------


def test_confirm_all_invalid_body_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A confirm-all body missing candidate_group_ids is rejected 400 before any write."""
    make_parallel_candidate_pair(project_db)

    response = _post(auth_client, _confirm_all_url(project.pk), {})

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _stored(project_db) == set()


def test_confirm_all_with_no_candidates_is_empty_noop(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all against an empty candidate set (empty client view) stores nothing."""
    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([]))

    assert response.status_code == 200
    assert response.json()["data"]["candidate_group_ids"] == []
    assert _stored(project_db) == set()


def test_confirm_success_envelope_shape(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """The confirm envelope is {timestamp, message, data} with a sorted id list.

    Three disjoint components are submitted in reverse-sorted order to prove the
    server sorts them itself rather than echoing the client's order.
    """
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=9)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=14)
    c1, c2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=16)
    comps = [
        _component_uuid(subject.id, [a1, a2]),
        _component_uuid(subject.id, [b1, b2]),
        _component_uuid(subject.id, [c1, c2]),
    ]
    sorted_ids = sorted(str(comp) for comp in comps)
    shuffled = [UUID(cid) for cid in sorted_ids[::-1]]

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, shuffled),
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    ids = payload["data"]["candidate_group_ids"]
    assert ids == sorted_ids
    assert ids != sorted_ids[::-1]  # a non-trivial ordering was actually applied
    datetime.datetime.fromisoformat(payload["timestamp"])


# ---------------------------------------------------------------------------
# -- Unconfirm one subject: not-confirmed and unknown are 200 no-ops
# ---------------------------------------------------------------------------


def test_unconfirm_subject_not_confirmed_removes_nothing(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE on a subject that was never confirmed returns 200 with data 0."""
    subject = make_subject(project_db, commit=False)
    make_parallel_candidate_pair(project_db, subject=subject)

    response = auth_client.delete(_confirmation_url(project.pk, subject.id))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == 0
    assert isinstance(data, int) and not isinstance(data, bool)
    assert _stored(project_db) == set()


def test_unconfirm_unknown_subject_is_noop(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE on a subject id with no candidates returns 200 with data 0."""
    make_parallel_candidate_pair(project_db)

    response = auth_client.delete(_confirmation_url(project.pk, uuid.uuid7()))

    assert response.status_code == 200
    assert response.json()["data"] == 0


def test_clear_all_confirmations_returns_int_count(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE / reports the number of rows removed as a JSON int, not a bool."""
    a, b = uuid.uuid7(), uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=a, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=b)

    response = auth_client.delete(_confirmations_url(project.pk))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == 2
    assert isinstance(data, int) and not isinstance(data, bool)


# ---------------------------------------------------------------------------
# -- Auth (401) across every confirmation verb
# ---------------------------------------------------------------------------


def test_confirm_all_unauthenticated_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all from a fresh client is rejected 401 before any write; nothing stored."""
    stored = uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=stored)

    response = _post(Client(), _confirm_all_url(project.pk), _confirm_all_body([]))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _stored(project_db) == {stored}


def test_clear_all_confirmations_unauthenticated_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """Clear-all confirmations from a fresh client is rejected 401; nothing removed."""
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7())

    response = Client().delete(_confirmations_url(project.pk))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert len(_stored(project_db)) == 1


def test_unconfirm_subject_unauthenticated_rejected(
    project: Project,
    project_db: Session,
) -> None:
    """Unconfirm-subject from a fresh client is rejected 401."""
    response = Client().delete(_confirmation_url(project.pk, uuid.uuid7()))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


# ---------------------------------------------------------------------------
# -- Unknown project (404) across every confirmation verb
# ---------------------------------------------------------------------------


def test_confirm_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm on a nonexistent project id -> 404 from require_project."""
    response = _post(
        auth_client,
        _confirmations_url(project.pk + 1000),
        _confirm_body(uuid.uuid7(), []),
    )

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_confirm_all_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all on a nonexistent project id -> 404 from require_project."""
    response = _post(auth_client, _confirm_all_url(project.pk + 1000), _confirm_all_body([]))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_clear_all_confirmations_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Clear-all confirmations on a nonexistent project id -> 404."""
    response = auth_client.delete(_confirmations_url(project.pk + 1000))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_unconfirm_subject_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Unconfirm-subject on a nonexistent project id -> 404."""
    response = auth_client.delete(_confirmation_url(project.pk + 1000, uuid.uuid7()))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


# ---------------------------------------------------------------------------
# -- Method dispatch (405) and path-converter routing (404)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put"])
def test_confirmations_collection_unsupported_methods_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """The confirmations collection defines only post/delete; get/put -> 405."""
    response = getattr(auth_client, method)(_confirmations_url(project.pk))
    assert response.status_code == 405


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_confirm_all_unsupported_methods_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """The confirm-all view defines only post; other verbs -> 405."""
    response = getattr(auth_client, method)(_confirm_all_url(project.pk))
    assert response.status_code == 405


@pytest.mark.parametrize("method", ["get", "post", "put"])
def test_confirmation_subject_unsupported_methods_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """The per-subject view defines only delete; other verbs -> 405."""
    response = getattr(auth_client, method)(_confirmation_url(project.pk, uuid.uuid7()))
    assert response.status_code == 405


def test_unconfirm_non_uuid_subject_id_does_not_match_route(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A non-uuid subject_id fails the ``<uuid:subject_id>`` converter -> Django 404."""
    response = auth_client.delete(
        f"/api/projects/{project.pk}/parallel-blocks/confirmations/not-a-uuid",
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# -- Cross-project isolation: every mutating verb touches only its own DB
# ---------------------------------------------------------------------------


def test_confirm_subject_scoped_to_this_project(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    """Confirming a subject in project A never touches project B's confirmations."""
    subject_a = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    comp_a = _component_uuid(subject_a.id, [a1, a2])
    b_conf = uuid.uuid7()
    make_confirmed_candidate(second_project_db, candidate_group_id=b_conf)

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject_a.id, [comp_a]),
    )

    assert response.status_code == 200
    assert _stored(project_db) == {comp_a}
    # Project B's own file is untouched.
    assert _stored(second_project_db) == {b_conf}


def test_confirm_all_scoped_to_this_project(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    """Confirm-all in project A never touches project B's confirmations."""
    subject_a = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    comp_a = _component_uuid(subject_a.id, [a1, a2])
    b_conf = uuid.uuid7()
    make_confirmed_candidate(second_project_db, candidate_group_id=b_conf)

    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp_a]))

    assert response.status_code == 200
    assert _stored(project_db) == {comp_a}
    assert _stored(second_project_db) == {b_conf}


def test_clear_all_confirmations_scoped_to_this_project(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    """Clearing project A's confirmations leaves project B's intact."""
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7())
    b_conf = uuid.uuid7()
    make_confirmed_candidate(second_project_db, candidate_group_id=b_conf)

    response = auth_client.delete(_confirmations_url(project.pk))

    assert response.status_code == 200
    assert _stored(project_db) == set()
    assert _stored(second_project_db) == {b_conf}


def test_unconfirm_subject_scoped_to_this_project(
    auth_client: Client,
    project: Project,
    project_db: Session,
    second_project: Project,
    second_project_db: Session,
) -> None:
    """Unconfirming a subject in project A leaves project B's confirmations intact."""
    subject_a = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    comp_a = _component_uuid(subject_a.id, [a1, a2])
    make_confirmed_candidate(project_db, candidate_group_id=comp_a)
    b_conf = uuid.uuid7()
    make_confirmed_candidate(second_project_db, candidate_group_id=b_conf)

    response = auth_client.delete(_confirmation_url(project.pk, subject_a.id))

    assert response.status_code == 200
    assert _stored(project_db) == set()
    assert _stored(second_project_db) == {b_conf}


# ---------------------------------------------------------------------------
# -- Idempotency: repeating a mutation never 500s and converges
# ---------------------------------------------------------------------------


def test_confirm_subject_twice_is_idempotent(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming the same subject twice returns 200 both times (no UNIQUE 500)."""
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    first = _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [comp]))
    second = _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [comp]))

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["candidate_group_ids"] == [str(comp)]
    assert _stored(project_db) == {comp}


def test_confirm_all_twice_is_idempotent(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all repeated returns 200 both times and stores each id once."""
    subject = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    first = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp]))
    second = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp]))

    assert first.status_code == 200
    assert second.status_code == 200
    assert _stored(project_db) == {comp}


def test_clear_all_confirmations_twice_second_is_zero(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A second clear-all reports 0 rows removed (idempotent)."""
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7())

    first = auth_client.delete(_confirmations_url(project.pk))
    second = auth_client.delete(_confirmations_url(project.pk))

    assert first.json()["data"] == 1
    assert second.status_code == 200
    assert second.json()["data"] == 0


# ---------------------------------------------------------------------------
# -- Confirm-all: success payload + more stale shapes
# ---------------------------------------------------------------------------


def test_confirm_all_success_data_is_sorted_ids(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """The confirm-all success payload echoes every stored id, sorted as strings.

    Three subjects' components are submitted in reverse-sorted order so an
    order-preserving bug can't slip through: the server must re-sort them.
    """
    subjects = [_make_subject_with_degree(project_db) for _ in range(3)]
    comps = [
        _component_uuid(subject.id, list(make_parallel_candidate_pair(project_db, subject=subject)))
        for subject in subjects
    ]
    sorted_ids = sorted(str(comp) for comp in comps)
    shuffled = [UUID(cid) for cid in sorted_ids[::-1]]

    response = _post(
        auth_client,
        _confirm_all_url(project.pk),
        _confirm_all_body(shuffled),
    )

    assert response.status_code == 200
    ids = response.json()["data"]["candidate_group_ids"]
    assert ids == sorted_ids
    assert ids != sorted_ids[::-1]  # a non-trivial ordering was actually applied


def test_confirm_subject_empty_view_against_live_candidates_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An empty client view for a subject that HAS live candidates is stale -> 409."""
    subject = make_subject(project_db, commit=False)
    make_parallel_candidate_pair(project_db, subject=subject)

    response = _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, []))

    assert response.status_code == 409
    assert response.json()["error"] == "projects.parallel_confirmation.stale"
    assert _stored(project_db) == set()


def test_confirm_subject_superset_view_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A client view carrying an extra id beyond the live set is stale -> 409."""
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [comp, uuid.uuid7()]),
    )

    assert response.status_code == 409
    assert _stored(project_db) == set()


def test_confirm_all_superset_view_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all with an extra id beyond the live set is stale -> 409."""
    subject = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    response = _post(
        auth_client,
        _confirm_all_url(project.pk),
        _confirm_all_body([comp, uuid.uuid7()]),
    )

    assert response.status_code == 409
    assert _stored(project_db) == set()


def test_unconfirm_subject_removes_all_its_components_count(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Unconfirming a subject with two components reports both rows removed (count 2)."""
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=9)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=14)
    comp_a = _component_uuid(subject.id, [a1, a2])
    comp_b = _component_uuid(subject.id, [b1, b2])
    _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [comp_a, comp_b]),
    )
    assert _stored(project_db) == {comp_a, comp_b}

    response = auth_client.delete(_confirmation_url(project.pk, subject.id))

    assert response.status_code == 200
    assert response.json()["data"] == 2
    assert _stored(project_db) == set()


# ---------------------------------------------------------------------------
# -- Body-validation matrix for the confirmation POST endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_body", ["[]", "5", '"a string"', "{not valid json"])
def test_confirm_subject_non_object_or_malformed_body_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    raw_body: str,
) -> None:
    """A non-object or malformed confirm-subject body -> 400, nothing stored."""
    response = _post_raw(auth_client, _confirmations_url(project.pk), raw_body)

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _stored(project_db) == set()


@pytest.mark.parametrize("raw_body", ["[]", "5", '"a string"', "{not valid json"])
def test_confirm_all_non_object_or_malformed_body_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    raw_body: str,
) -> None:
    """A non-object or malformed confirm-all body -> 400, nothing stored."""
    response = _post_raw(auth_client, _confirm_all_url(project.pk), raw_body)

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _stored(project_db) == set()


def test_confirm_subject_missing_candidate_ids_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Omitting candidate_group_ids -> 400 naming the field, nothing stored."""
    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        {"subject_id": str(uuid.uuid7())},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "generic.invalid_body"
    assert "candidate_group_ids" in payload["message"]
    assert _stored(project_db) == set()


@pytest.mark.parametrize(
    "body",
    [
        {"subject_id": "not-a-uuid", "candidate_group_ids": []},
        {"subject_id": str(uuid.uuid7()), "candidate_group_ids": ["also-bad"]},
    ],
    ids=["bad_subject_id", "bad_candidate_id"],
)
def test_confirm_subject_non_uuid_fields_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
    body: dict,
) -> None:
    """Non-UUID subject_id or candidate id -> 400 invalid_body, nothing stored."""
    response = _post(auth_client, _confirmations_url(project.pk), body)

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _stored(project_db) == set()


def test_confirm_all_non_uuid_candidate_id_rejected(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A non-UUID id in the confirm-all body -> 400 invalid_body, nothing stored."""
    response = _post(
        auth_client,
        _confirm_all_url(project.pk),
        {"candidate_group_ids": ["not-a-uuid"]},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert _stored(project_db) == set()


# ---------------------------------------------------------------------------
# -- DELETE-vs-POST guard asymmetry: unconfirm removes by the *live* id
# ---------------------------------------------------------------------------


def test_unconfirm_subject_ignores_stale_view_no_409(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE /<subject_id> has no stale guard: it removes by the live id only.

    Unlike the POST confirm endpoints, unconfirm never returns 409. After the
    subject's live candidate id shifts (a third block joins the slot), the stale
    stored id no longer matches the live one, so the delete removes nothing (0)
    and leaves the stale row untouched.
    """
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)
    comp_ab = _component_uuid(subject.id, [block_a, block_b])
    _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [comp_ab]))
    assert _stored(project_db) == {comp_ab}

    # A third colliding block grows the component: the live id is now {a,b,c}.
    block_c = _add_block_to_subject_slot(project_db, subject)
    comp_abc = _component_uuid(subject.id, [block_a, block_b, block_c])
    assert comp_abc != comp_ab

    response = auth_client.delete(_confirmation_url(project.pk, subject.id))

    assert response.status_code == 200  # never 409, even though the view is stale
    assert response.json()["data"] == 0  # the live {a,b,c} id matched no stored row
    assert _stored(project_db) == {comp_ab}  # the stale {a,b} row survives unchanged


# ---------------------------------------------------------------------------
# -- Confirmation ops never touch the separate "finish" flag
# ---------------------------------------------------------------------------


def test_confirmation_ops_leave_finish_flag_untouched(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """No confirmation verb flips ``has_selected_parallel_sessions`` (a separate flag).

    Only "Terminar" (the finish endpoint) sets that flag; confirm-subject,
    confirm-all, clear-all, and unconfirm-subject must leave it False throughout.
    """
    subject = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    assert _flag(project.pk) is False

    # confirm-subject
    _post(auth_client, _confirmations_url(project.pk), _confirm_body(subject.id, [comp]))
    assert _flag(project.pk) is False

    # confirm-all
    _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body([comp]))
    assert _flag(project.pk) is False

    # unconfirm-subject
    auth_client.delete(_confirmation_url(project.pk, subject.id))
    assert _flag(project.pk) is False

    # clear-all
    auth_client.delete(_confirmations_url(project.pk))
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- Confirming one subject never confirms a sibling
# ---------------------------------------------------------------------------


def test_confirm_subject_leaves_sibling_subject_unconfirmed(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming subject A stores only A's component; sibling B stays unconfirmed."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject_a)
    make_parallel_candidate_pair(project_db, subject=subject_b)
    comp_a = _component_uuid(subject_a.id, [a1, a2])

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject_a.id, [comp_a]),
    )

    assert response.status_code == 200
    assert _stored(project_db) == {comp_a}
    flags = _confirmed_by_subject(auth_client, project.pk)
    assert flags == {str(subject_a.id): True, str(subject_b.id): False}


# ---------------------------------------------------------------------------
# -- Cross-table isolation: confirmations never touch confirmed-group members
# ---------------------------------------------------------------------------


def test_clear_all_confirmations_leaves_group_members_intact(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """DELETE / clears confirmations but never the separate group-member table."""
    group_id = uuid.uuid7()
    members = {(group_id, uuid.uuid7()), (group_id, uuid.uuid7())}
    for gid, block_id in members:
        make_group_member(project_db, group_id=gid, original_block_id=block_id, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7())

    response = auth_client.delete(_confirmations_url(project.pk))

    assert response.status_code == 200
    assert _stored(project_db) == set()
    # The confirmed-group membership rows are a different table -- untouched.
    assert _group_members(project_db) == members


def test_confirm_subject_leaves_group_members_intact(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirming a subject never adds to or removes from the group-member table."""
    group_id = uuid.uuid7()
    members = {(group_id, uuid.uuid7()), (group_id, uuid.uuid7())}
    for gid, block_id in members:
        make_group_member(project_db, group_id=gid, original_block_id=block_id, commit=False)
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject)
    comp = _component_uuid(subject.id, [a1, a2])

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [comp]),
    )

    assert response.status_code == 200
    assert _stored(project_db) == {comp}
    assert _group_members(project_db) == members


# ---------------------------------------------------------------------------
# -- Confirm-all over a range of subject counts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_subjects", [3, 5])
def test_confirm_all_confirms_every_subject_n_subjects(
    auth_client: Client,
    project: Project,
    project_db: Session,
    n_subjects: int,
) -> None:
    """Confirm-all with the full live id set stores every subject's component."""
    subjects = [_make_subject_with_degree(project_db) for _ in range(n_subjects)]
    comps = {
        _component_uuid(subject.id, list(make_parallel_candidate_pair(project_db, subject=subject)))
        for subject in subjects
    }

    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body(list(comps)))

    assert response.status_code == 200
    assert _stored(project_db) == comps
    assert set(_confirmed_by_subject(auth_client, project.pk).values()) == {True}


def test_confirm_all_omitting_one_subject_is_stale(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Confirm-all whose body drops one subject's id is stale -> 409, nothing stored."""
    subjects = [_make_subject_with_degree(project_db) for _ in range(3)]
    comps = [
        _component_uuid(subject.id, list(make_parallel_candidate_pair(project_db, subject=subject)))
        for subject in subjects
    ]

    # Drop the last subject's id: the client's view no longer matches the live set.
    response = _post(auth_client, _confirm_all_url(project.pk), _confirm_all_body(comps[:-1]))

    assert response.status_code == 409
    assert response.json()["error"] == "projects.parallel_confirmation.stale"
    assert _stored(project_db) == set()
