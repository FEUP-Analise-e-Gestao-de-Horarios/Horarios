"""Integration tests for GET ``/api/projects/<pk>/parallel-blocks/candidates``.

Every test drives the real endpoint through the Django test client against a
per-project SQLite file seeded (and committed) via the ``project_db`` fixture
and the ``make_*`` factories. Assertions target the *wire* payload
(``response.json()``): UUIDs are strings, dates are ``"YYYY-MM-DD"`` and
``WeekDay`` values are lowercase English. This module owns the candidates GET
route, including its decorator ordering and its no-trailing-slash contract.
"""

import datetime
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
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.parallel_blocks import ParallelCandidateGroupResponse
from src.users.models import User
from tests.factories import (
    make_class,
    make_degree,
    make_group_member,
    make_parallel_candidate_pair,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)

CANDIDATES_MESSAGE = "Candidate parallel groups retrieved successfully"

# Distinct degree acronyms are handed out per test since ``Degree.acronym`` is
# UNIQUE and the factory default ("LEI") collides when two subjects each
# auto-create a parent degree. Callers needing several independent subjects use
# ``_make_subject_with_degree`` below.
_ACRONYM_POOL = iter(f"D{n:03d}" for n in range(1000))


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------


def _candidates_url(project_id: int) -> str:
    """The candidates route is registered WITHOUT a trailing slash."""
    return f"/api/projects/{project_id}/parallel-blocks/candidates"


def _get_candidates(client: Client, project_id: int):
    return client.get(_candidates_url(project_id))


def _groups_by_id(payload: dict) -> dict[str, dict]:
    """Index the (order-non-deterministic) group list by candidate_group_id."""
    return {group["candidate_group_id"]: group for group in payload["data"]}


def _groups_by_subject(payload: dict) -> dict[str, dict]:
    """Index groups by subject id (feasible when subjects are distinct)."""
    return {group["subject"]["id"]: group for group in payload["data"]}


def _expected_group_id(subject_id: UUID, block_ids) -> str:
    """Recompute the wire candidate_group_id the DAO would emit."""
    return str(_component_uuid(subject_id, sorted(block_ids)))


def _make_subject_with_degree(session: Session):
    """A subject linked to a fresh year under a degree with a unique acronym.

    ``Degree.acronym`` is UNIQUE, so tests needing several independent subjects
    cannot rely on the factory default acronym.
    """
    degree = make_degree(session, acronym=next(_ACRONYM_POOL), commit=False)
    year = make_year(session, degree=degree, commit=False)
    return make_subject(session, year=year, commit=False)


def _seed_block(
    session: Session,
    *,
    subject,
    block_id: UUID,
    slots,
    class_row=None,
    year=None,
) -> None:
    """Seed one block spanning ``slots`` (list of ``(weekday, start_time, week)``).

    A single class is reused across all sessions of the block.
    """
    if class_row is None:
        class_row = make_class(session, year=year, commit=False)
    for weekday, start_time, week in slots:
        session_row = make_session(
            session,
            week=week,
            weekday=weekday,
            start_time=start_time,
            original_block_id=block_id,
            commit=False,
        )
        make_session_class_subject(
            session,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
            commit=False,
        )


# ---------------------------------------------------------------------------
# -- Decorator ordering / routing (P0/P1)
# ---------------------------------------------------------------------------


def test_unauthenticated_request_rejected_401(
    project: Project,
    project_db: Session,
) -> None:
    """A fresh client (no login) is rejected 401 before touching the project DB."""
    response = _get_candidates(Client(), project.pk)

    assert response.status_code == 401
    body = response.json()
    assert body == {
        "error": "auth.not_authenticated",
        "message": "User is not authenticated.",
    }


def test_unauthenticated_unknown_project_still_401(
    project: Project,
) -> None:
    """require_auth wraps require_project: auth failure beats the 404."""
    response = _get_candidates(Client(), project.pk + 1000)

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_unknown_project_returns_404_for_authenticated_user(
    auth_client: Client,
    project: Project,
) -> None:
    """An authenticated user hitting a missing project id gets 404."""
    response = _get_candidates(auth_client, project.pk + 1000)

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_project_owned_by_other_user_still_returns_200(
    project: Project,
    project_db: Session,
) -> None:
    """require_project performs no ownership check (possible authz gap)."""
    other = User.objects.create_user(
        email="other@example.com",
        username="other",
        password="test-pass-1234",
        is_active=True,
    )
    other_client = Client()
    other_client.force_login(other)

    response = _get_candidates(other_client, project.pk)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_candidates_with_trailing_slash_returns_404(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """The candidates route has no trailing slash; adding one 404s."""
    response = auth_client.get(f"/api/projects/{project.pk}/parallel-blocks/candidates/")

    assert response.status_code == 404
    # Contrast: the canonical no-slash route is reachable and returns 200.
    assert _get_candidates(auth_client, project.pk).status_code == 200


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_candidates_unsupported_methods_return_405(
    auth_client: Client,
    project: Project,
    project_db: Session,
    method: str,
) -> None:
    """The candidates view defines only ``get``; other methods fall through to 405."""
    response = getattr(auth_client, method)(_candidates_url(project.pk))
    assert response.status_code == 405


@pytest.fixture
def project_b(project: Project, settings, tmp_path) -> Iterator[Project]:
    """A second project with its own empty per-project DB under the shared tmp path.

    ``project`` (via ``project_db``) already points ``PROJECTS_DB_PATH`` at
    ``tmp_path``; this provisions a distinct project row plus its own database
    beneath the same root and evicts the engine on teardown.
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


def test_candidates_cross_project_isolation(
    auth_client: Client,
    project: Project,
    project_db: Session,
    project_b: Project,
) -> None:
    """Project A has a candidate group; GET on empty project B returns none of it."""
    subject = make_subject(project_db, commit=False)
    make_parallel_candidate_pair(project_db, subject=subject)

    # A has one candidate group; B's own DB is empty.
    assert len(_get_candidates(auth_client, project.pk).json()["data"]) == 1

    response = _get_candidates(auth_client, project_b.pk)
    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# -- Empty / no-candidate paths (P0)
# ---------------------------------------------------------------------------


def test_empty_db_returns_empty_data_and_full_envelope(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An empty seeded DB returns 200, data == [] and the success envelope."""
    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert payload["message"] == CANDIDATES_MESSAGE
    assert payload["data"] == []
    assert isinstance(payload["timestamp"], str)


def test_single_block_no_shared_slot_returns_empty(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A lone block shares no slot, so it is dropped (singleton) -> data []."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    _seed_block(
        project_db,
        subject=subject,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, datetime.date(2025, 9, 15))],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_block_only_one_has_scs_does_not_fabricate_partner(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A session with no SCS link never becomes a candidate (inner join)."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    # block_a: bare session, no SessionClassSubject.
    make_session(
        project_db,
        week=datetime.date(2025, 9, 15),
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=uuid.uuid7(),
        commit=False,
    )
    # block_b: fully linked, same slot.
    _seed_block(
        project_db,
        subject=subject,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, datetime.date(2025, 9, 15))],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_same_slot_different_subjects_do_not_merge(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two blocks in the same (week, weekday, start) but different subjects: no group."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    week = datetime.date(2025, 9, 15)
    _seed_block(
        project_db,
        subject=subject_a,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, week)],
        year=subject_a.years[0],
    )
    _seed_block(
        project_db,
        subject=subject_b,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, week)],
        year=subject_b.years[0],
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# -- Happy path: single pair (P0)
# ---------------------------------------------------------------------------


def test_two_blocks_sharing_slot_full_response(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A single pair yields exactly one fully-validating candidate group."""
    subject = make_subject(project_db, commit=False)
    subject_id = subject.id
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == CANDIDATES_MESSAGE
    assert len(payload["data"]) == 1

    group = payload["data"][0]
    validated = ParallelCandidateGroupResponse.model_validate(group)
    assert validated.candidate_group_id == _component_uuid(subject_id, [block_a, block_b])

    assert group["candidate_group_id"] == _expected_group_id(subject_id, [block_a, block_b])
    assert group["weekday"] == "monday"
    assert group["subject"]["id"] == str(subject_id)

    nodes = group["nodes"]
    assert [n["original_block_id"] for n in nodes] == [str(block_a), str(block_b)]
    for node in nodes:
        assert node["confirmed_group_id"] is None
        assert node["first_week"] == "2025-09-15"
        assert node["last_week"] == "2025-09-15"
        assert node["session"] == {"type": "T", "start_time": 9, "duration": 2}
        assert isinstance(node["classes"], list)
        assert node["classes"]
        for cls in node["classes"]:
            assert set(cls) == {"id", "code", "year_id"}

    assert len(group["edges"]) == 1


def test_edge_shape_for_single_shared_week(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """The single edge is canonically sorted with the shared week."""
    block_a, block_b = make_parallel_candidate_pair(project_db)

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    edges = payload["data"][0]["edges"]
    assert len(edges) == 1
    edge = edges[0]
    assert edge["source"] == str(block_a)
    assert edge["target"] == str(block_b)
    assert edge["weeks"] == ["2025-09-15"]


def test_weekday_and_dates_serialized_as_strings(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """weekday and every date come out as JSON strings in canonical form."""
    make_parallel_candidate_pair(
        project_db,
        weekday=WeekDay.WEDNESDAY,
        week=datetime.date(2025, 10, 1),
    )

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    assert group["weekday"] == "wednesday"
    assert isinstance(group["weekday"], str)
    for node in group["nodes"]:
        assert node["first_week"] == "2025-10-01"
        assert node["last_week"] == "2025-10-01"
        assert isinstance(node["original_block_id"], str)
        assert node["confirmed_group_id"] is None
    assert group["edges"][0]["weeks"] == ["2025-10-01"]
    assert all(isinstance(w, str) for w in group["edges"][0]["weeks"])


@pytest.mark.parametrize(
    ("weekday_arg", "expected_wire"),
    [
        (WeekDay.THURSDAY, "thursday"),
        (WeekDay("terça"), "tuesday"),
    ],
)
def test_representative_weekday_and_alias_roundtrip(
    auth_client: Client,
    project: Project,
    project_db: Session,
    weekday_arg: WeekDay,
    expected_wire: str,
) -> None:
    """weekday reflects the representative block; PT aliases round-trip to English."""
    make_parallel_candidate_pair(project_db, weekday=weekday_arg, start_time=14)

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    assert group["weekday"] == expected_wire
    for node in group["nodes"]:
        assert node["session"] == {"type": "T", "start_time": 14, "duration": 2}


# ---------------------------------------------------------------------------
# -- Multi-week aggregation / block week range (P0)
# ---------------------------------------------------------------------------


def test_multi_week_collision_aggregates_sorted_edge_and_spans_nodes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two blocks colliding on two out-of-order weeks -> one sorted edge; node span."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    later = datetime.date(2025, 9, 22)
    earlier = datetime.date(2025, 9, 15)

    block_ids = []
    for _ in range(2):
        block_id = uuid.uuid7()
        _seed_block(
            project_db,
            subject=subject,
            block_id=block_id,
            slots=[
                (WeekDay.MONDAY, 9, later),
                (WeekDay.MONDAY, 9, earlier),
            ],
            year=year,
        )
        block_ids.append(block_id)
    block_a, block_b = sorted(block_ids)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    edge = group["edges"][0]
    assert edge["source"] == str(block_a)
    assert edge["target"] == str(block_b)
    assert edge["weeks"] == ["2025-09-15", "2025-09-22"]
    for node in group["nodes"]:
        assert node["first_week"] == "2025-09-15"
        assert node["last_week"] == "2025-09-22"


# ---------------------------------------------------------------------------
# -- Eligibility filter (heterogeneous blocks) (P1/P2)
# ---------------------------------------------------------------------------


def test_heterogeneous_block_dropped_breaks_group(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A block spanning two distinct slots is dropped, leaving no pair -> data []."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    w1 = datetime.date(2025, 9, 15)
    w2 = datetime.date(2025, 9, 22)
    # block_a: two different slots (different weeks, so the (week, block) unique
    # constraint holds) -> heterogeneous -> dropped.
    _seed_block(
        project_db,
        subject=subject,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, w1), (WeekDay.TUESDAY, 9, w2)],
        year=year,
    )
    # block_b: clean Monday/9 only.
    _seed_block(
        project_db,
        subject=subject,
        block_id=uuid.uuid7(),
        slots=[(WeekDay.MONDAY, 9, w1)],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_heterogeneous_dropped_but_homogeneous_pair_forms_group(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A dropped heterogeneous block never appears; a clean pair still groups."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    w1 = datetime.date(2025, 9, 15)
    w2 = datetime.date(2025, 9, 22)

    # Heterogeneous block_x: Monday/9 (w1) + Tuesday/9 (w2) -> dropped even
    # though its Monday/9 slot overlaps the clean pair below.
    hetero_id = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject,
        block_id=hetero_id,
        slots=[(WeekDay.MONDAY, 9, w1), (WeekDay.TUESDAY, 9, w2)],
        year=year,
    )
    # Clean homogeneous pair a/b on Monday/9 (w1).
    clean = []
    for _ in range(2):
        block_id = uuid.uuid7()
        _seed_block(
            project_db,
            subject=subject,
            block_id=block_id,
            slots=[(WeekDay.MONDAY, 9, w1)],
            year=year,
        )
        clean.append(block_id)
    block_a, block_b = sorted(clean)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    node_ids = [n["original_block_id"] for n in group["nodes"]]
    assert node_ids == [str(block_a), str(block_b)]
    assert str(hetero_id) not in node_ids


# ---------------------------------------------------------------------------
# -- Multi-subject blocks (P0/P1)
# ---------------------------------------------------------------------------


def test_multi_subject_block_appears_once_per_subject(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A block shared by two subjects yields two groups, not a merged one."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    year = subject_a.years[0]
    week = datetime.date(2025, 9, 15)

    # block1: one session, two classes -> two SCS, one per subject.
    block1 = uuid.uuid7()
    session1 = make_session(
        project_db,
        week=week,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block1,
        commit=False,
    )
    class1a = make_class(project_db, year=year, commit=False)
    class1b = make_class(project_db, year=year, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session1,
        class_row=class1a,
        subject=subject_a,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session1,
        class_row=class1b,
        subject=subject_b,
        commit=False,
    )

    # block2 collides with block1 under subject_a.
    block2 = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject_a,
        block_id=block2,
        slots=[(WeekDay.MONDAY, 9, week)],
        year=year,
    )
    # block3 collides with block1 under subject_b.
    block3 = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject_b,
        block_id=block3,
        slots=[(WeekDay.MONDAY, 9, week)],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 2
    by_subject = _groups_by_subject(payload)
    assert set(by_subject) == {str(subject_a.id), str(subject_b.id)}

    group_a = by_subject[str(subject_a.id)]
    group_b = by_subject[str(subject_b.id)]
    members_a = {n["original_block_id"] for n in group_a["nodes"]}
    members_b = {n["original_block_id"] for n in group_b["nodes"]}
    assert members_a == {str(block1), str(block2)}
    assert members_b == {str(block1), str(block3)}


def test_multi_subject_group_edges_carry_only_that_subjects_weeks(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Each per-subject edge carries only that subject's collision weeks."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    year = subject_a.years[0]
    w1 = datetime.date(2025, 9, 15)
    w2 = datetime.date(2025, 9, 22)

    # block1 taught under both subjects, both weeks. Two classes (uq_session_class).
    block1 = uuid.uuid7()
    class1a = make_class(project_db, year=year, commit=False)
    class1b = make_class(project_db, year=year, commit=False)
    for wk in (w1, w2):
        srow = make_session(
            project_db,
            week=wk,
            weekday=WeekDay.MONDAY,
            start_time=9,
            original_block_id=block1,
            commit=False,
        )
        make_session_class_subject(
            project_db,
            session_row=srow,
            class_row=class1a,
            subject=subject_a,
            commit=False,
        )
        make_session_class_subject(
            project_db,
            session_row=srow,
            class_row=class1b,
            subject=subject_b,
            commit=False,
        )

    # block2 collides with block1 under subject_a on w1 and w2.
    block2 = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject_a,
        block_id=block2,
        slots=[(WeekDay.MONDAY, 9, w1), (WeekDay.MONDAY, 9, w2)],
        year=year,
    )
    # block3 collides with block1 under subject_b on w1 only.
    block3 = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject_b,
        block_id=block3,
        slots=[(WeekDay.MONDAY, 9, w1)],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    by_subject = _groups_by_subject(payload)
    edge_a = by_subject[str(subject_a.id)]["edges"][0]
    edge_b = by_subject[str(subject_b.id)]["edges"][0]
    assert edge_a["weeks"] == ["2025-09-15", "2025-09-22"]
    assert edge_b["weeks"] == ["2025-09-15"]


# ---------------------------------------------------------------------------
# -- Confirmed group id surfacing (P0/P1/P2)
# ---------------------------------------------------------------------------


def test_confirmed_group_id_on_every_confirmed_node(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Both members of a saved group surface the same confirmed_group_id."""
    block_a, block_b = make_parallel_candidate_pair(project_db, commit=False)
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a, commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b, commit=False)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    nodes = payload["data"][0]["nodes"]
    assert all(n["confirmed_group_id"] == str(group_id) for n in nodes)


def test_confirmed_group_id_null_for_unconfirmed_mixed_in_group(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Only the confirmed block carries its group id; the other is null."""
    block_a, block_b = make_parallel_candidate_pair(project_db, commit=False)
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a, commit=False)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    nodes = {n["original_block_id"]: n for n in payload["data"][0]["nodes"]}
    assert nodes[str(block_a)]["confirmed_group_id"] == str(group_id)
    assert nodes[str(block_b)]["confirmed_group_id"] is None


def test_get_is_read_only_no_membership_changes(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """GET performs no writes: membership rows are unchanged afterwards."""
    from sqlalchemy import select

    from src.projects.projects_db.models import ParallelBlockGroupMember

    def _membership() -> set[tuple[str, str]]:
        return {
            (str(m.parallel_block_group_id), str(m.original_block_id))
            for m in project_db.scalars(select(ParallelBlockGroupMember)).all()
        }

    block_a, _block_b = make_parallel_candidate_pair(project_db, commit=False)
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a, commit=False)
    project_db.commit()

    before = _membership()

    assert _get_candidates(auth_client, project.pk).status_code == 200

    project_db.expire_all()
    after = _membership()
    assert before == after == {(str(group_id), str(block_a))}


# ---------------------------------------------------------------------------
# -- Node ordering / union-find topology (P1)
# ---------------------------------------------------------------------------


def _seed_three_block_clique(
    session: Session,
    *,
    subject,
    year,
    week: datetime.date,
    block_ids: list[UUID],
) -> None:
    """Three blocks all sharing one Monday/9 slot on ``week``."""
    for block_id in block_ids:
        _seed_block(
            session,
            subject=subject,
            block_id=block_id,
            slots=[(WeekDay.MONDAY, 9, week)],
            year=year,
        )


def test_nodes_sorted_by_block_id_regardless_of_insertion_order(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Nodes come back ascending by original_block_id even if inserted unsorted."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    week = datetime.date(2025, 9, 15)

    ids = sorted(uuid.uuid7() for _ in range(3))
    insertion_order = [ids[2], ids[0], ids[1]]
    _seed_three_block_clique(
        project_db,
        subject=subject,
        year=year,
        week=week,
        block_ids=insertion_order,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    node_ids = [n["original_block_id"] for n in payload["data"][0]["nodes"]]
    assert node_ids == [str(i) for i in ids]


def test_three_blocks_one_slot_single_component(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Three blocks in one slot: one component, 3 nodes, 3 canonical edges."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    week = datetime.date(2025, 9, 15)

    ids = sorted(uuid.uuid7() for _ in range(3))
    _seed_three_block_clique(project_db, subject=subject, year=year, week=week, block_ids=ids)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    assert [n["original_block_id"] for n in group["nodes"]] == [str(i) for i in ids]

    edges = group["edges"]
    assert len(edges) == 3
    pairs = {(e["source"], e["target"]) for e in edges}
    a, b, c = (str(i) for i in ids)
    assert pairs == {(a, b), (a, c), (b, c)}
    # Every edge is canonically sorted (source < target).
    for e in edges:
        assert e["source"] < e["target"]


def test_transitive_chain_across_weeks_merges_one_component(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """a-b collide on W1, b-c on W2: union-find merges all three; no a-c edge."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    w1 = datetime.date(2025, 9, 15)
    w2 = datetime.date(2025, 9, 22)

    a, b, c = sorted(uuid.uuid7() for _ in range(3))
    # a: only W1
    _seed_block(project_db, subject=subject, block_id=a, slots=[(WeekDay.MONDAY, 9, w1)], year=year)
    # b: both weeks
    _seed_block(
        project_db,
        subject=subject,
        block_id=b,
        slots=[(WeekDay.MONDAY, 9, w1), (WeekDay.MONDAY, 9, w2)],
        year=year,
    )
    # c: only W2
    _seed_block(project_db, subject=subject, block_id=c, slots=[(WeekDay.MONDAY, 9, w2)], year=year)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    assert [n["original_block_id"] for n in group["nodes"]] == [str(a), str(b), str(c)]

    edges = {(e["source"], e["target"]): e["weeks"] for e in group["edges"]}
    ab = tuple(sorted((str(a), str(b))))
    bc = tuple(sorted((str(b), str(c))))
    ac = tuple(sorted((str(a), str(c))))
    assert edges[ab] == ["2025-09-15"]
    assert edges[bc] == ["2025-09-22"]
    assert ac not in edges


# ---------------------------------------------------------------------------
# -- subject.years aggregation (P1/P2)
# ---------------------------------------------------------------------------


def test_subject_years_aggregate_dedup_and_ordered(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """subject.years dedups by year id and orders by (year_number, degree_acronym)."""
    from sqlalchemy import insert

    from src.projects.projects_db.models._secondary_tables import subject_years

    # Three degrees / three year rows: (2,'ZEB'), (1,'LEI'), (1,'AAA').
    d_zeb = make_degree(project_db, acronym="ZEB", name="Zeta Eng", commit=False)
    year_zeb = make_year(project_db, degree=d_zeb, number=2, commit=False)
    d_lei = make_degree(project_db, acronym="LEI", name="Lic Eng Info", commit=False)
    year_lei = make_year(project_db, degree=d_lei, number=1, commit=False)
    d_aaa = make_degree(project_db, acronym="AAA", name="Alpha", commit=False)
    year_aaa = make_year(project_db, degree=d_aaa, number=1, commit=False)

    subject = make_subject(project_db, year=year_zeb, commit=False)
    # Link the subject to all three years via the m2m (not strictly needed for
    # the DAO, which reads years off the classes, but keeps the model honest).
    for y in (year_lei, year_aaa):
        project_db.execute(insert(subject_years).values(subject_id=subject.id, year_id=y.id))

    week = datetime.date(2025, 9, 15)
    # block_a: classes in year_zeb and year_lei.
    block_a = uuid.uuid7()
    sa = make_session(
        project_db,
        week=week,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block_a,
        commit=False,
    )
    for y in (year_zeb, year_lei):
        cls = make_class(project_db, year=y, commit=False)
        make_session_class_subject(
            project_db,
            session_row=sa,
            class_row=cls,
            subject=subject,
            commit=False,
        )
    # block_b: classes in year_lei (shared) and year_aaa.
    block_b = uuid.uuid7()
    sb = make_session(
        project_db,
        week=week,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block_b,
        commit=False,
    )
    for y in (year_lei, year_aaa):
        cls = make_class(project_db, year=y, commit=False)
        make_session_class_subject(
            project_db,
            session_row=sb,
            class_row=cls,
            subject=subject,
            commit=False,
        )
    project_db.commit()

    id_zeb, id_lei, id_aaa = str(year_zeb.id), str(year_lei.id), str(year_aaa.id)

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    years = group["subject"]["years"]
    # Dedup: year_lei appears once despite being on both blocks.
    assert [y["id"] for y in years] == [id_aaa, id_lei, id_zeb]
    for y in years:
        assert set(y["degree"]) == {"id", "acronym", "name"}
    # Each year carries its number (used for labels/ordering on the client).
    assert [y["number"] for y in years] == [1, 1, 2]
    degree_acronyms = [y["degree"]["acronym"] for y in years]
    assert degree_acronyms == ["AAA", "LEI", "ZEB"]


def test_subject_years_only_includes_component_subjects_years(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A class also taught under another subject/year does not leak its years."""
    subject_a = _make_subject_with_degree(project_db)
    year_a = subject_a.years[0]
    subject_b = _make_subject_with_degree(project_db)
    # Give subject_b its own distinct year (under a fresh degree).
    degree_b = make_degree(project_db, acronym=next(_ACRONYM_POOL), commit=False)
    year_b = make_year(project_db, degree=degree_b, number=3, commit=False)

    week = datetime.date(2025, 9, 15)

    # block_a: one class in year_a taught under subject_a; the same session's
    # class also taught (extra SCS via a second class) under subject_b/year_b.
    block_a = uuid.uuid7()
    sa = make_session(
        project_db,
        week=week,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block_a,
        commit=False,
    )
    cls_a = make_class(project_db, year=year_a, commit=False)
    cls_b = make_class(project_db, year=year_b, commit=False)
    make_session_class_subject(
        project_db,
        session_row=sa,
        class_row=cls_a,
        subject=subject_a,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=sa,
        class_row=cls_b,
        subject=subject_b,
        commit=False,
    )

    # block_b: only subject_a / year_a, collides with block_a.
    block_b = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject_a,
        block_id=block_b,
        slots=[(WeekDay.MONDAY, 9, week)],
        year=year_a,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    group_a = _groups_by_subject(payload)[str(subject_a.id)]
    year_ids = {y["id"] for y in group_a["subject"]["years"]}
    assert year_ids == {str(year_a.id)}
    assert str(year_b.id) not in year_ids


# ---------------------------------------------------------------------------
# -- Class aggregation within a node (P2)
# ---------------------------------------------------------------------------


def test_classes_within_node_sorted_by_code(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A node's classes are aggregated and sorted by class code, no duplicates."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    week = datetime.date(2025, 9, 15)

    # block with a single session, two classes 'C-ZZ' and 'C-AA'.
    block1 = uuid.uuid7()
    s1 = make_session(
        project_db,
        week=week,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block1,
        commit=False,
    )
    cls_zz = make_class(project_db, year=year, code="C-ZZ", commit=False)
    cls_aa = make_class(project_db, year=year, code="C-AA", commit=False)
    make_session_class_subject(
        project_db,
        session_row=s1,
        class_row=cls_zz,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=s1,
        class_row=cls_aa,
        subject=subject,
        commit=False,
    )

    # Another block to make it a candidate pair.
    block2 = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject,
        block_id=block2,
        slots=[(WeekDay.MONDAY, 9, week)],
        year=year,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    nodes = {n["original_block_id"]: n for n in payload["data"][0]["nodes"]}
    classes = nodes[str(block1)]["classes"]
    codes = [c["code"] for c in classes]
    assert codes == ["C-AA", "C-ZZ"]
    for c in classes:
        assert c["year_id"] == str(year.id)
    # No duplicates.
    assert len({c["id"] for c in classes}) == len(classes)


# ---------------------------------------------------------------------------
# -- Determinism / multiple groups (P1)
# ---------------------------------------------------------------------------


def test_candidate_group_id_deterministic_across_gets(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """The candidate_group_id is stable across repeated GETs."""
    subject = make_subject(project_db, commit=False)
    subject_id = subject.id
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    first_payload = _get_candidates(auth_client, project.pk).json()
    second_payload = _get_candidates(auth_client, project.pk).json()
    assert len(first_payload["data"]) == 1
    assert len(second_payload["data"]) == 1
    first = first_payload["data"][0]
    second = second_payload["data"][0]

    expected = _expected_group_id(subject_id, [block_a, block_b])
    assert first["candidate_group_id"] == second["candidate_group_id"] == expected


def test_multiple_independent_groups_all_returned(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Two disjoint pairs (different subjects/slots) both come back."""
    subject_a = _make_subject_with_degree(project_db)
    subject_b = _make_subject_with_degree(project_db)
    a1, a2 = make_parallel_candidate_pair(
        project_db,
        subject=subject_a,
        weekday=WeekDay.MONDAY,
        start_time=9,
        commit=False,
    )
    b1, b2 = make_parallel_candidate_pair(
        project_db,
        subject=subject_b,
        weekday=WeekDay.FRIDAY,
        start_time=11,
        commit=False,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 2
    by_id = _groups_by_id(payload)
    assert set(by_id) == {
        _expected_group_id(subject_a.id, [a1, a2]),
        _expected_group_id(subject_b.id, [b1, b2]),
    }
    for group in payload["data"]:
        validated = ParallelCandidateGroupResponse.model_validate(group)
        assert len(validated.nodes) == 2
        assert len(validated.edges) == 1


# ---------------------------------------------------------------------------
# -- Envelope + rich round-trip + invariant (P0/P1/P2)
# ---------------------------------------------------------------------------


def test_full_envelope_shape_on_populated_get(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A populated GET returns the full JSON success envelope."""
    make_parallel_candidate_pair(project_db)

    response = _get_candidates(auth_client, project.pk)

    assert response["Content-Type"] == "application/json"
    payload = response.json()
    assert set(payload) == {"timestamp", "message", "data"}
    assert payload["message"] == CANDIDATES_MESSAGE
    assert isinstance(payload["timestamp"], str)
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) == 1


def test_rich_group_round_trips_through_response_schema(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """A fully-connected 3-block group with rich detail validates end-to-end."""
    from sqlalchemy import insert

    from src.projects.projects_db.models._secondary_tables import subject_years

    # Subject taught in two years across two degrees.
    d_lei = make_degree(project_db, acronym="LEI", name="Lic Eng Info", commit=False)
    year1 = make_year(project_db, degree=d_lei, number=1, commit=False)
    d_meec = make_degree(project_db, acronym="MEEC", name="Mestrado EEC", commit=False)
    year2 = make_year(project_db, degree=d_meec, number=2, commit=False)

    subject = make_subject(project_db, year=year1, commit=False)
    project_db.execute(insert(subject_years).values(subject_id=subject.id, year_id=year2.id))

    week = datetime.date(2025, 9, 15)
    ids = sorted(uuid.uuid7() for _ in range(3))

    # block[0]: two classes (year1 + year2); block[1], block[2]: one class year1.
    for idx, block_id in enumerate(ids):
        srow = make_session(
            project_db,
            week=week,
            weekday=WeekDay.MONDAY,
            start_time=9,
            original_block_id=block_id,
            commit=False,
        )
        if idx == 0:
            for y in (year1, year2):
                cls = make_class(project_db, year=y, commit=False)
                make_session_class_subject(
                    project_db,
                    session_row=srow,
                    class_row=cls,
                    subject=subject,
                    commit=False,
                )
        else:
            cls = make_class(project_db, year=year1, commit=False)
            make_session_class_subject(
                project_db,
                session_row=srow,
                class_row=cls,
                subject=subject,
                commit=False,
            )

    # Confirm block ids[0] into a group.
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=ids[0], commit=False)
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    validated = ParallelCandidateGroupResponse.model_validate(group)

    assert len(validated.nodes) == 3
    assert len(validated.edges) == 3
    assert len(validated.subject.years) == 2

    confirmed = {str(n.original_block_id): n.confirmed_group_id for n in validated.nodes}
    assert confirmed[str(ids[0])] == group_id
    assert confirmed[str(ids[1])] is None
    assert confirmed[str(ids[2])] is None


def test_edge_endpoints_are_subset_of_node_ids(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """Invariant/positive control: every edge endpoint is one of the node ids."""
    ids = sorted(uuid.uuid7() for _ in range(3))
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    _seed_three_block_clique(
        project_db,
        subject=subject,
        year=year,
        week=datetime.date(2025, 9, 15),
        block_ids=ids,
    )
    project_db.commit()

    response = _get_candidates(auth_client, project.pk)

    payload = response.json()
    assert len(payload["data"]) == 1
    group = payload["data"][0]
    node_ids = {n["original_block_id"] for n in group["nodes"]}
    for edge in group["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
