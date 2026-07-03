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
from src.projects.projects_db.models import ParallelConfirmedCandidate
from tests.factories import (
    make_confirmed_candidate,
    make_degree,
    make_parallel_candidate_pair,
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
    """A fresh client is rejected 401 on the confirm endpoint."""
    response = _post(Client(), _confirmations_url(project.pk), {"subject_id": str(uuid.uuid7())})

    assert response.status_code == 401


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
    """The confirm envelope is {timestamp, message, data} with a sorted id list."""
    subject = make_subject(project_db, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=9)
    b1, b2 = make_parallel_candidate_pair(project_db, subject=subject, start_time=14)
    comp_a = _component_uuid(subject.id, [a1, a2])
    comp_b = _component_uuid(subject.id, [b1, b2])

    response = _post(
        auth_client,
        _confirmations_url(project.pk),
        _confirm_body(subject.id, [comp_a, comp_b]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    ids = payload["data"]["candidate_group_ids"]
    assert ids == sorted([str(comp_a), str(comp_b)])
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
    """Confirm-all from a fresh client is rejected 401 before any write."""
    response = _post(Client(), _confirm_all_url(project.pk), _confirm_all_body([]))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


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
