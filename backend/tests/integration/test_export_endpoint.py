"""Integration tests for ``POST /api/projects/<pk>/export`` (``ProjectExportView``).

Drives the whole exporter pipeline through the Django test client against two
seeded per-project SQLite files: auth/project guards, the diff → conflicts →
modification-steps computation, compact/expanded response formatting, and the
export cache (cache hit vs forced recalculation).
"""

import json

from django.test import Client
from pytest import mark

from src.projects.projects_db.dao.export_cache_dao import ExportCacheDAO
from tests.integration._export_seed import (
    CLASS_A,
    CLASS_B,
    ROOM_A,
    SUBJECT_A,
    TEACHER_A,
    TEACHER_B,
    seed_reference_data,
    seed_session,
    uid,
)


def _export_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/export"


def _post(client: Client, project_id: int, body: dict | str | None = None):
    if body is None:
        return client.post(_export_url(project_id))
    data = body if isinstance(body, str) else json.dumps(body)
    return client.post(_export_url(project_id), data=data, content_type="application/json")


def _seed_move(export_dbs):
    """Seed one session moved from 08:30 to 10:00; return its UUID."""
    session_id = uid(100)
    block = uid(200)
    seed_reference_data(export_dbs.initial)
    seed_session(export_dbs.initial, session_id=session_id, start_time=830, original_block_id=block)
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=session_id,
        start_time=1000,
        original_block_id=block,
    )
    return session_id


# ---------------------------------------------------------------------------
# -- Auth / project / method guards
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(project) -> None:
    response = _post(Client(), project.pk, {})
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_unknown_project_returns_404(auth_client: Client, project) -> None:
    response = _post(auth_client, project.pk + 1000, {})
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


@mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_non_post_methods_return_405(auth_client: Client, project, method: str) -> None:
    response = getattr(auth_client, method)(_export_url(project.pk))
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# -- No changes
# ---------------------------------------------------------------------------


def test_identical_databases_return_empty_compact_payload(auth_client: Client, export_dbs) -> None:
    session_id = uid(100)
    block = uid(200)
    for db in (export_dbs.initial, export_dbs.general):
        seed_reference_data(db)
        seed_session(db, session_id=session_id, start_time=830, original_block_id=block)

    response = _post(auth_client, export_dbs.project_id, {})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Project export computed successfully"
    data = body["data"]
    assert data["format"] == "compact_export_v1"
    assert data["modification_steps"] == []
    assert data["conflicts"] == []
    assert data["added_removed_sessions"] == {"added": [], "removed": []}


# ---------------------------------------------------------------------------
# -- Move (compact & expanded)
# ---------------------------------------------------------------------------


def test_move_compact_payload(auth_client: Client, export_dbs) -> None:
    session_id = _seed_move(export_dbs)

    response = _post(auth_client, export_dbs.project_id, {})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["format"] == "compact_export_v1"
    assert len(data["modification_steps"]) == 1
    step = data["modification_steps"][0]
    assert step["type"] == "move"
    # Step ids are normalized hex; the hoisted session entity is keyed by the
    # hyphenated snapshot id (find_entity bridges the two on expansion).
    assert step["session_ids"] == [session_id.hex]
    assert str(session_id) in data["entities"]["sessions"]


def test_move_expanded_payload(auth_client: Client, export_dbs) -> None:
    session_id = _seed_move(export_dbs)

    response = _post(auth_client, export_dbs.project_id, {"payload_format": "expanded"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert "format" not in data
    assert len(data["modification_steps"]) == 1
    step = data["modification_steps"][0]
    assert step["type"] == "move"
    assert step["modifications"]["start_time"] == {"old": 830, "new": 1000}
    assert step["session"]["id"] == str(session_id)
    assert step["session"]["rooms"] == ["B101"]
    assert step["session"]["classes"] == ["1LEIC01"]


@mark.parametrize("payload_format", ["weird", "COMPACT", "", None, 123])
def test_invalid_payload_format_defaults_to_compact(
    auth_client: Client,
    export_dbs,
    payload_format: object,
) -> None:
    _seed_move(export_dbs)

    response = _post(auth_client, export_dbs.project_id, {"payload_format": payload_format})

    assert response.status_code == 200
    assert response.json()["data"]["format"] == "compact_export_v1"


def test_malformed_json_body_is_tolerated(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    response = _post(auth_client, export_dbs.project_id, "this is not json")

    assert response.status_code == 200
    # Defaults kick in (compact, recalc off), and the move is still computed.
    data = response.json()["data"]
    assert data["format"] == "compact_export_v1"
    assert len(data["modification_steps"]) == 1


def test_missing_body_is_tolerated(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    response = _post(auth_client, export_dbs.project_id, None)

    assert response.status_code == 200
    assert response.json()["data"]["format"] == "compact_export_v1"


def test_non_object_json_body_is_tolerated(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    # A JSON array is valid JSON but not an object: it is ignored, defaults apply.
    response = _post(auth_client, export_dbs.project_id, "[1, 2, 3]")

    assert response.status_code == 200
    assert response.json()["data"]["format"] == "compact_export_v1"


# ---------------------------------------------------------------------------
# -- Exchange
# ---------------------------------------------------------------------------


def test_exact_swap_reported_as_exchange(auth_client: Client, export_dbs) -> None:
    session_a = uid(101)
    session_b = uid(102)
    block_a = uid(201)
    block_b = uid(202)
    for db, (a_start, b_start) in (
        (export_dbs.initial, (830, 1000)),
        (export_dbs.general, (1000, 830)),
    ):
        seed_reference_data(db)
        seed_session(
            db,
            session_id=session_a,
            start_time=a_start,
            original_block_id=block_a,
            rooms=(ROOM_A,),
        )
        seed_session(
            db,
            session_id=session_b,
            start_time=b_start,
            original_block_id=block_b,
            rooms=(ROOM_A,),
            class_subjects=((CLASS_B, SUBJECT_A),),
        )

    response = _post(auth_client, export_dbs.project_id, {"payload_format": "expanded"})

    assert response.status_code == 200
    steps = response.json()["data"]["modification_steps"]
    assert len(steps) == 2
    assert {step["type"] for step in steps} == {"exchange"}


# ---------------------------------------------------------------------------
# -- Added / removed sessions
# ---------------------------------------------------------------------------


def test_added_and_removed_sessions_are_reported(auth_client: Client, export_dbs) -> None:
    added_id = uid(110)
    removed_id = uid(111)
    seed_reference_data(export_dbs.initial)
    # Only in the initial DB -> removed.
    seed_session(
        export_dbs.initial,
        session_id=removed_id,
        start_time=830,
        original_block_id=uid(210),
    )
    seed_reference_data(export_dbs.general)
    # Only in the general DB -> added.
    seed_session(
        export_dbs.general,
        session_id=added_id,
        start_time=1000,
        original_block_id=uid(211),
    )

    response = _post(auth_client, export_dbs.project_id, {})

    assert response.status_code == 200
    data = response.json()["data"]
    added_removed = data["added_removed_sessions"]
    assert {record["id"] for record in added_removed["added"]} == {added_id.hex}
    assert {record["id"] for record in added_removed["removed"]} == {removed_id.hex}
    # Neither an added nor a removed session is a modification.
    assert data["modification_steps"] == []


# ---------------------------------------------------------------------------
# -- Conflicts
# ---------------------------------------------------------------------------


def test_room_conflict_is_reported(auth_client: Client, export_dbs) -> None:
    session_1 = uid(120)
    session_2 = uid(121)
    for db in (export_dbs.initial, export_dbs.general):
        seed_reference_data(db)
        # Two overlapping sessions sharing room A but with disjoint teachers and
        # classes, so only a room conflict is produced.
        seed_session(
            db,
            session_id=session_1,
            start_time=830,
            original_block_id=uid(220),
            rooms=(ROOM_A,),
            teachers=(TEACHER_A,),
            class_subjects=((CLASS_A, SUBJECT_A),),
        )
        seed_session(
            db,
            session_id=session_2,
            start_time=845,
            original_block_id=uid(221),
            rooms=(ROOM_A,),
            teachers=(TEACHER_B,),
            class_subjects=((CLASS_B, SUBJECT_A),),
        )

    response = _post(auth_client, export_dbs.project_id, {"payload_format": "expanded"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["rooms_conflicts"]) == 1
    conflict = data["rooms_conflicts"][0]
    assert conflict["room_name"] == "B101"
    assert conflict["collisions"] == 2
    # Conflict session ids come from hydrated UUID columns -> hyphenated form.
    assert {str(session_1), str(session_2)} == set(conflict["session_ids"])
    assert data["teacher_conflicts"] == []
    assert data["classes_conflicts"] == []


# ---------------------------------------------------------------------------
# -- Caching
# ---------------------------------------------------------------------------


def test_second_call_is_served_from_cache(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    first = _post(auth_client, export_dbs.project_id, {})
    second = _post(auth_client, export_dbs.project_id, {})

    assert first.json()["message"] == "Project export computed successfully"
    assert second.json()["message"] == "Project export loaded from cache"
    # The cached payload matches the freshly computed one.
    assert second.json()["data"] == first.json()["data"]


def test_legacy_non_compact_cache_is_discarded_and_recomputed(
    auth_client: Client,
    export_dbs,
) -> None:
    _seed_move(export_dbs)

    # Simulate a cache entry written in an old, non-compact format.
    ExportCacheDAO(export_dbs.general).replace_project_export_payload({"legacy": "payload"})
    export_dbs.general.commit()

    response = _post(auth_client, export_dbs.project_id, {})

    assert response.status_code == 200
    body = response.json()
    # The stale entry is dropped and a fresh compact payload is computed.
    assert body["message"] == "Project export computed successfully"
    assert body["data"]["format"] == "compact_export_v1"
    assert len(body["data"]["modification_steps"]) == 1


def test_recalculate_flag_forces_recomputation(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    _post(auth_client, export_dbs.project_id, {})
    recomputed = _post(auth_client, export_dbs.project_id, {"recalculate_export_graph": True})

    assert recomputed.json()["message"] == "Project export computed successfully"
    assert len(recomputed.json()["data"]["modification_steps"]) == 1


def test_reuses_cached_modification_steps_when_only_payload_cache_cleared(
    auth_client: Client,
    export_dbs,
) -> None:
    _seed_move(export_dbs)

    # First call fills both the compact payload cache and the modification-step
    # cache. Clearing only the payload cache forces a recompute of conflicts
    # while the cached modification steps are reused.
    _post(auth_client, export_dbs.project_id, {})
    ExportCacheDAO(export_dbs.general).clear_project_export_payload()
    export_dbs.general.commit()

    response = _post(auth_client, export_dbs.project_id, {})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Project export computed successfully"
    steps = body["data"]["modification_steps"]
    assert len(steps) == 1
    assert steps[0]["type"] == "move"


def test_cache_returns_requested_format(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    # Prime the cache with a compact computation.
    _post(auth_client, export_dbs.project_id, {})
    # Then request the cached data in expanded form.
    cached_expanded = _post(auth_client, export_dbs.project_id, {"payload_format": "expanded"})

    assert cached_expanded.json()["message"] == "Project export loaded from cache"
    data = cached_expanded.json()["data"]
    assert "format" not in data
    assert data["modification_steps"][0]["type"] == "move"


# ---------------------------------------------------------------------------
# -- Response envelope
# ---------------------------------------------------------------------------


def test_response_envelope_has_message_and_data(auth_client: Client, export_dbs) -> None:
    _seed_move(export_dbs)

    body = _post(auth_client, export_dbs.project_id, {}).json()

    assert set(body) >= {"message", "data", "timestamp"}
