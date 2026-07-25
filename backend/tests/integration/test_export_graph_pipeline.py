"""Integration tests for :class:`ExportGraph` against real project databases.

These seed the ``initial`` and ``general`` SQLite files, run the exact diff the
endpoint runs (``SessionDAO.get_changes_only`` across an ``ATTACH``-ed initial
database), feed the result to ``ExportGraph`` and assert on the modification
steps. This exercises the loaders (``ExportGraphSnapshotLoader`` /
``ResourceOccupancyLoader``), the dependency graph, move/exchange
classification and recurring-block grouping end to end — everything except the
HTTP layer, which ``test_export_endpoint.py`` covers.
"""

from src.exporter.export_graph import ExportGraph
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session, init_engine
from tests.integration._export_seed import (
    CLASS_A,
    CLASS_B,
    ROOM_A,
    ROOM_B,
    SUBJECT_A,
    TEACHER_A,
    TEACHER_B,
    WEEK,
    WEEK_2,
    seed_reference_data,
    seed_session,
    uid,
)


def build_graph(project_id: int) -> tuple[dict, ExportGraph]:
    """Compute the change set the endpoint would compute and build the graph."""
    init_engine(general_db(project_id))
    with get_session(general_db(project_id)) as session:
        dao = SessionDAO(session)
        alias = dao.attach_db(initial_db(project_id))
        try:
            changes = dao.get_changes_only(alias)
        finally:
            dao.detach_db(alias)

    return changes, ExportGraph(changes, project_id)


# ---------------------------------------------------------------------------
# -- No changes
# ---------------------------------------------------------------------------


def test_identical_databases_produce_no_changes_and_no_steps(export_dbs) -> None:
    session_id = uid(100)
    block = uid(200)
    for db in (export_dbs.initial, export_dbs.general):
        seed_reference_data(db)
        seed_session(db, session_id=session_id, start_time=830, original_block_id=block)

    changes, graph = build_graph(export_dbs.project_id)

    assert changes == {}
    assert graph.build_modification_steps() == []


# ---------------------------------------------------------------------------
# -- Time move
# ---------------------------------------------------------------------------


def test_start_time_move_produces_single_move_step_with_snapshot(export_dbs) -> None:
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

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    assert len(steps) == 1
    step = steps[0]
    assert step["type"] == "move"
    # The exporter carries hyphen-less (normalized) ids throughout, matching the
    # Uuid(native_uuid=False) storage form.
    assert step["session_ids"] == [session_id.hex]
    assert step["modifications"]["start_time"] == {"old": 830, "new": 1000}

    # The snapshot is loaded from the initial DB and enriched by the loaders.
    session = step["session"]
    assert session["start_time"] == 830
    assert session["rooms"] == ["B101"]
    assert session["classes"] == ["1LEIC01"]
    assert session["teachers"][0]["acronym"] == "AA"
    assert session["subjects"][0]["acronym"] == "IA"
    assert step["applies_to_all_weeks"] is True


# ---------------------------------------------------------------------------
# -- Resource changes
# ---------------------------------------------------------------------------


def test_room_change_produces_room_modification(export_dbs) -> None:
    session_id = uid(100)
    block = uid(200)
    seed_reference_data(export_dbs.initial)
    seed_session(
        export_dbs.initial,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        rooms=(ROOM_A,),
    )
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        rooms=(ROOM_B,),
    )

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    assert len(steps) == 1
    rooms_change = steps[0]["modifications"]["rooms"]
    assert [room["room_name"] for room in rooms_change["added"]] == ["B102"]
    assert [room["room_name"] for room in rooms_change["removed"]] == ["B101"]


def test_teacher_change_produces_teacher_modification(export_dbs) -> None:
    session_id = uid(100)
    block = uid(200)
    seed_reference_data(export_dbs.initial)
    seed_session(
        export_dbs.initial,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        teachers=(TEACHER_A,),
    )
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        teachers=(TEACHER_B,),
    )

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    teachers_change = steps[0]["modifications"]["teachers"]
    assert [t["teacher_acronym"] for t in teachers_change["added"]] == ["BB"]
    assert [t["teacher_acronym"] for t in teachers_change["removed"]] == ["AA"]


def test_class_subject_change_produces_class_subject_modification(export_dbs) -> None:
    session_id = uid(100)
    block = uid(200)
    seed_reference_data(export_dbs.initial)
    seed_session(
        export_dbs.initial,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        class_subjects=((CLASS_A, SUBJECT_A),),
    )
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=session_id,
        start_time=830,
        original_block_id=block,
        class_subjects=((CLASS_B, SUBJECT_A),),
    )

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    change = steps[0]["modifications"]["class_subjects"]
    assert [c["class_code"] for c in change["added"]] == ["1LEIC02"]
    assert [c["class_code"] for c in change["removed"]] == ["1LEIC01"]


# ---------------------------------------------------------------------------
# -- Exchange vs move classification (via real occupancy)
# ---------------------------------------------------------------------------


def _seed_two_session_swap(
    export_dbs,
    *,
    a_initial: int,
    a_general: int,
    b_initial: int,
    b_general: int,
) -> tuple[str, str]:
    session_a = uid(101)
    session_b = uid(102)
    block_a = uid(201)
    block_b = uid(202)

    for db, (a_start, b_start) in (
        (export_dbs.initial, (a_initial, b_initial)),
        (export_dbs.general, (a_general, b_general)),
    ):
        seed_reference_data(db)
        # Both sessions share room A so their moves interact in the graph.
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
    return session_a.hex, session_b.hex


def test_exact_time_swap_is_classified_as_exchange(export_dbs) -> None:
    session_a, session_b = _seed_two_session_swap(
        export_dbs,
        a_initial=830,
        a_general=1000,
        b_initial=1000,
        b_general=830,
    )

    _changes, graph = build_graph(export_dbs.project_id)
    ordered = dict(graph.get_graph_ordered_modifications())

    assert ordered[session_a] == "exchange"
    assert ordered[session_b] == "exchange"

    steps = graph.build_modification_steps()
    assert {step["type"] for step in steps} == {"exchange"}
    # The two sessions belong to different blocks -> two grouped steps that
    # depend on each other.
    assert len(steps) == 2


def test_offset_time_cycle_is_classified_as_move(export_dbs) -> None:
    session_a, session_b = _seed_two_session_swap(
        export_dbs,
        a_initial=830,
        a_general=1030,
        b_initial=1000,
        b_general=830,
    )

    _changes, graph = build_graph(export_dbs.project_id)
    ordered = dict(graph.get_graph_ordered_modifications())

    # A cycle, but not an exact slot exchange -> both classified as moves.
    assert ordered[session_a] == "move"
    assert ordered[session_b] == "move"


# ---------------------------------------------------------------------------
# -- Recurring-block grouping across weeks
# ---------------------------------------------------------------------------


def test_recurring_block_moved_in_all_weeks_collapses_to_one_step(export_dbs) -> None:
    block = uid(300)
    week_1_id = uid(301)
    week_2_id = uid(302)

    for db, start_time in ((export_dbs.initial, 830), (export_dbs.general, 1000)):
        seed_reference_data(db)
        seed_session(
            db,
            session_id=week_1_id,
            start_time=start_time,
            original_block_id=block,
            week=WEEK,
        )
        seed_session(
            db,
            session_id=week_2_id,
            start_time=start_time,
            original_block_id=block,
            week=WEEK_2,
        )

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    # Same block, same change in both weeks -> a single grouped step.
    assert len(steps) == 1
    step = steps[0]
    assert set(step["session_ids"]) == {week_1_id.hex, week_2_id.hex}
    assert step["weeks"] == ["2026-01-05", "2026-01-12"]
    assert step["applies_to_all_weeks"] is True
    assert step["week_range"] == {
        "start": "2026-01-05",
        "end": "2026-01-12",
        "contiguous": True,
    }


def test_partial_recurring_block_move_is_not_all_weeks(export_dbs) -> None:
    block = uid(300)
    week_1_id = uid(301)
    week_2_id = uid(302)

    # Both weeks exist in the block, but only the first week is moved.
    seed_reference_data(export_dbs.initial)
    seed_session(
        export_dbs.initial,
        session_id=week_1_id,
        start_time=830,
        original_block_id=block,
        week=WEEK,
    )
    seed_session(
        export_dbs.initial,
        session_id=week_2_id,
        start_time=830,
        original_block_id=block,
        week=WEEK_2,
    )
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=week_1_id,
        start_time=1000,
        original_block_id=block,
        week=WEEK,
    )
    seed_session(
        export_dbs.general,
        session_id=week_2_id,
        start_time=830,
        original_block_id=block,
        week=WEEK_2,
    )

    _changes, graph = build_graph(export_dbs.project_id)
    steps = graph.build_modification_steps()

    assert len(steps) == 1
    step = steps[0]
    assert step["session_ids"] == [week_1_id.hex]
    assert step["applies_to_all_weeks"] is False
