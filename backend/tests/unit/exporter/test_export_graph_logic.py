"""Unit tests for :class:`src.exporter.export_graph.ExportGraph` pure logic.

These exercise the graph algorithm without a database by constructing an
``ExportGraph`` via ``__new__`` and setting only the attributes each method
reads (the same technique the in-repo ``src/exporter/tests.py`` uses). The
end-to-end pipeline against a real seeded database is covered separately in
``tests/integration/test_export_graph_pipeline.py``.
"""

import datetime

import networkx as nx
from pytest import mark, raises

from src.exporter.export_graph import ExportGraph
from src.exporter.export_graph_types import (
    ResourceMovement,
    ResourceSpec,
    TimeMovement,
    TimePlacement,
)


def make_graph(**attrs: object) -> ExportGraph:
    """Build an uninitialized ``ExportGraph`` with the given attributes set."""
    graph = ExportGraph.__new__(ExportGraph)
    graph.dependency_graph = None
    for name, value in attrs.items():
        setattr(graph, name, value)
    return graph


ROOM_SPEC = ResourceSpec("rooms", "room_ids", "rooms", "room_id")


# ---------------------------------------------------------------------------
# -- Change-shape predicates
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("change", "expected"),
    [
        ({"old": 1, "new": 2}, True),
        ({"old": None, "new": 2}, True),
        ({"old": 1}, False),
        ({"new": 2}, False),
        ({"added": [], "removed": []}, False),
        (None, False),
        ("not-a-dict", False),
    ],
)
def test_is_column_change(change: object, expected: bool) -> None:
    assert ExportGraph.is_column_change(change) is expected  # type: ignore[arg-type]


@mark.parametrize(
    ("change", "expected"),
    [
        ({"added": [{"room_id": "r"}], "removed": []}, True),
        ({"added": [], "removed": [{"room_id": "r"}]}, True),
        ({"added": [], "removed": []}, False),
        ({"old": 1, "new": 2}, False),
        (None, False),
        ("x", False),
    ],
)
def test_is_relation_change(change: object, expected: bool) -> None:
    assert ExportGraph.is_relation_change(change) is expected  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# -- get_relation_ids
# ---------------------------------------------------------------------------


def test_get_relation_ids_normalizes_and_skips_rows_without_key() -> None:
    change = {
        "added": [
            {"room_id": "aa-bb"},
            {"room_id": "cc"},
            {"teacher_id": "no-room-key"},
        ],
    }
    assert ExportGraph.get_relation_ids(change, "added", "room_id") == {"aabb", "cc"}


def test_get_relation_ids_returns_empty_for_missing_bucket() -> None:
    assert ExportGraph.get_relation_ids({"removed": []}, "added", "room_id") == set()
    assert ExportGraph.get_relation_ids(None, "added", "room_id") == set()


# ---------------------------------------------------------------------------
# -- get_old_resources
# ---------------------------------------------------------------------------


def test_get_old_resources_without_relation_change_returns_sorted_current() -> None:
    graph = make_graph()
    assert graph.get_old_resources(("b", "a"), None, "room_id") == ("a", "b")


def test_get_old_resources_reconstructs_from_added_and_removed() -> None:
    graph = make_graph()
    # current = {a, b}; a was added and c was removed, so old = {b, c}.
    change = {"added": [{"room_id": "a"}], "removed": [{"room_id": "c"}]}
    assert graph.get_old_resources(("a", "b"), change, "room_id") == ("b", "c")


def test_get_old_resources_normalizes_hyphenated_ids() -> None:
    graph = make_graph()
    change = {"added": [{"room_id": "a-a"}], "removed": []}
    # current {aa, b}; aa was added -> old = {b}.
    assert graph.get_old_resources(("aa", "b"), change, "room_id") == ("b",)


# ---------------------------------------------------------------------------
# -- build_current_placement / build_time_movement
# ---------------------------------------------------------------------------


def test_build_current_placement_expands_slots() -> None:
    graph = make_graph()
    placement = graph.build_current_placement(
        {"start_time": 1000, "duration": 2, "weekday": "monday", "week": "2026-01-05"},
    )
    assert placement == TimePlacement(
        time_slots=(600, 630),
        weekday="monday",
        week="2026-01-05",
    )


def test_build_time_movement_uses_old_column_values_when_changed() -> None:
    graph = make_graph()
    session_data = {
        "start_time": 1000,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
    }
    changes = {"start_time": {"old": 830, "new": 1000}}

    movement = graph.build_time_movement(session_data, changes)

    assert movement.old.time_slots == (510, 540)
    assert movement.new.time_slots == (600, 630)
    assert movement.changed is True


def test_build_time_movement_falls_back_to_current_values_when_unchanged() -> None:
    graph = make_graph()
    session_data = {
        "start_time": 1000,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
    }
    # Only a room relation changed: the time did not move.
    changes = {"rooms": {"added": [{"room_id": "r"}], "removed": []}}

    movement = graph.build_time_movement(session_data, changes)

    assert movement.old.time_slots == (600, 630)
    assert movement.new.time_slots == (600, 630)
    assert movement.changed is False


def test_build_time_movement_tracks_week_and_weekday_moves() -> None:
    graph = make_graph()
    session_data = {
        "start_time": 830,
        "duration": 2,
        "weekday": "tuesday",
        "week": "2026-01-12",
    }
    changes = {
        "weekday": {"old": "monday", "new": "tuesday"},
        "week": {"old": "2026-01-05", "new": "2026-01-12"},
    }

    movement = graph.build_time_movement(session_data, changes)

    assert movement.old.weekday == "monday"
    assert movement.old.week == "2026-01-05"
    assert movement.new.weekday == "tuesday"
    assert movement.new.week == "2026-01-12"
    assert movement.changed is True


# ---------------------------------------------------------------------------
# -- build_resource_movement
# ---------------------------------------------------------------------------


def test_build_resource_movement_reads_current_and_reconstructs_old() -> None:
    graph = make_graph()
    session_data = {"room_ids": ("a", "b")}
    changes = {"rooms": {"added": [{"room_id": "a"}], "removed": [{"room_id": "c"}]}}

    movement = graph.build_resource_movement(session_data, changes, ROOM_SPEC)

    assert movement.new == ("a", "b")
    assert movement.old == ("b", "c")
    assert movement.changed is True


def test_build_resource_movement_unchanged_when_no_relation_diff() -> None:
    graph = make_graph()
    session_data = {"room_ids": ("a", "b")}

    movement = graph.build_resource_movement(session_data, {}, ROOM_SPEC)

    assert movement.new == ("a", "b")
    assert movement.old == ("a", "b")
    assert movement.changed is False


# ---------------------------------------------------------------------------
# -- add_change_edges
# ---------------------------------------------------------------------------


def test_add_change_edges_records_moving_session_on_edge() -> None:
    graph = nx.DiGraph()
    resources = ResourceMovement(old=("r1",), new=("r1",))
    time = TimeMovement(
        old=TimePlacement(time_slots=(510,), weekday="monday", week="w"),
        new=TimePlacement(time_slots=(600,), weekday="monday", week="w"),
        changed=True,
    )

    ExportGraph.add_change_edges(graph, "sessA", resources, time, include_shared_resources=True)

    old_node = ("r1", 510, "monday", "w")
    new_node = ("r1", 600, "monday", "w")
    assert graph.has_edge(old_node, new_node)
    assert graph.edges[old_node, new_node]["ids"] == ["sessA"]
    # Freshly created endpoint nodes start with empty occupancy.
    assert graph.nodes[new_node]["ids"] == []


def test_add_change_edges_appends_multiple_sessions_to_shared_edge() -> None:
    graph = nx.DiGraph()
    resources = ResourceMovement(old=("r1",), new=("r1",))
    time = TimeMovement(
        old=TimePlacement(time_slots=(510,), weekday="monday", week="w"),
        new=TimePlacement(time_slots=(600,), weekday="monday", week="w"),
        changed=True,
    )

    ExportGraph.add_change_edges(graph, "A", resources, time, include_shared_resources=True)
    ExportGraph.add_change_edges(graph, "B", resources, time, include_shared_resources=True)

    old_node = ("r1", 510, "monday", "w")
    new_node = ("r1", 600, "monday", "w")
    assert graph.edges[old_node, new_node]["ids"] == ["A", "B"]


# ---------------------------------------------------------------------------
# -- build_change_dependency_graph
# ---------------------------------------------------------------------------


def _room_graph_with_move(
    old_node: tuple,
    new_node: tuple,
    *,
    moving: list[str],
    occupying: list[str],
) -> dict[str, nx.DiGraph]:
    """Room resource graph: ``moving`` moves off ``old_node`` occupied by ``occupying``."""
    graph = nx.DiGraph()
    graph.add_node(old_node, ids=occupying)
    graph.add_node(new_node, ids=[])
    graph.add_edge(old_node, new_node, ids=moving)
    return {"rooms": graph, "teachers": nx.DiGraph(), "classes": nx.DiGraph()}


def test_build_change_dependency_graph_links_mover_to_slot_occupant() -> None:
    graph = make_graph(changes={"A": {}, "B": {}})
    old_node = ("r1", 510, "monday", "w")
    new_node = ("r1", 600, "monday", "w")
    graphs = _room_graph_with_move(old_node, new_node, moving=["A"], occupying=["B"])

    dependency_graph = graph.build_change_dependency_graph(graphs)

    assert set(dependency_graph.nodes) == {"A", "B"}
    assert dependency_graph.has_edge("A", "B")


def test_build_change_dependency_graph_ignores_self_dependency() -> None:
    graph = make_graph(changes={"A": {}})
    old_node = ("r1", 510, "monday", "w")
    new_node = ("r1", 600, "monday", "w")
    # A both moves off and occupies the node: no self-edge should be created.
    graphs = _room_graph_with_move(old_node, new_node, moving=["A"], occupying=["A"])

    dependency_graph = graph.build_change_dependency_graph(graphs)

    assert list(dependency_graph.edges) == []


def test_build_change_dependency_graph_ignores_unchanged_occupants() -> None:
    graph = make_graph(changes={"A": {}})
    old_node = ("r1", 510, "monday", "w")
    new_node = ("r1", 600, "monday", "w")
    # The slot is occupied by an unchanged session "X" not in changes.
    graphs = _room_graph_with_move(old_node, new_node, moving=["A"], occupying=["X"])

    dependency_graph = graph.build_change_dependency_graph(graphs)

    assert list(dependency_graph.edges) == []
    assert set(dependency_graph.nodes) == {"A"}


# ---------------------------------------------------------------------------
# -- get_dependencies
# ---------------------------------------------------------------------------


def _chain_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B"), ("B", "C")])
    return graph


def test_get_dependencies_direct_predecessors_only() -> None:
    graph = make_graph(dependency_graph=_chain_graph())
    deps = graph.get_dependencies()
    assert deps["A"] == []
    assert deps["B"] == ["A"]
    assert deps["C"] == ["B"]


def test_get_dependencies_transitive_includes_full_chain() -> None:
    graph = make_graph(dependency_graph=_chain_graph())
    deps = graph.get_dependencies(transitive=True)
    assert deps["A"] == []
    assert deps["B"] == ["A"]
    assert deps["C"] == ["A", "B"]


# ---------------------------------------------------------------------------
# -- ordering & class clustering
# ---------------------------------------------------------------------------


def test_order_change_groups_clusters_by_shared_classes() -> None:
    # Three independent changes; A and C share class X, B has class Y. The
    # class-aware topological sort keeps the two X groups adjacent.
    dependency_graph = nx.DiGraph()
    dependency_graph.add_nodes_from(["A", "B", "C"])
    graph = make_graph(
        dependency_graph=dependency_graph,
        sessions_by_change_key={
            "A": {"classes": ["X"]},
            "B": {"classes": ["Y"]},
            "C": {"classes": ["X"]},
        },
    )

    groups = graph.order_change_groups_using_graph()

    assert groups == [["A"], ["C"], ["B"]]


def test_order_change_groups_respects_dependency_order() -> None:
    dependency_graph = nx.DiGraph()
    dependency_graph.add_edges_from([("A", "B")])
    graph = make_graph(
        dependency_graph=dependency_graph,
        sessions_by_change_key={"A": {"classes": ["X"]}, "B": {"classes": ["Y"]}},
    )

    groups = graph.order_change_groups_using_graph()

    # A depends on B, so B must be ordered before A (predecessors first).
    assert groups == [["A"], ["B"]]


def test_topological_sort_by_classes_raises_on_cycle() -> None:
    graph = make_graph(sessions_by_change_key={})
    cyclic = nx.DiGraph()
    cyclic.add_node(0, members={"A"})
    cyclic.add_node(1, members={"B"})
    cyclic.add_edges_from([(0, 1), (1, 0)])

    with raises(nx.NetworkXUnfeasible):
        graph.topological_sort_by_classes(cyclic)


def test_class_priority_key_prefers_class_overlap_then_stable_order() -> None:
    graph = make_graph(
        sessions_by_change_key={"A": {"classes": ["X", "Y"]}, "B": {"classes": ["Z"]}},
    )

    overlap_key = graph.class_priority_key({"A"}, {"X"})
    no_overlap_key = graph.class_priority_key({"B"}, {"X"})

    # More overlap sorts first (negative overlap count).
    assert overlap_key[0] == -1
    assert no_overlap_key[0] == 0
    assert overlap_key < no_overlap_key


# ---------------------------------------------------------------------------
# -- exchange classification
# ---------------------------------------------------------------------------


def _swap_graph(start_times: dict[str, tuple[int, int]]) -> ExportGraph:
    dependency_graph = nx.DiGraph()
    dependency_graph.add_edges_from([("a", "b"), ("b", "a")])
    return make_graph(
        changes={
            session_id: {"start_time": {"old": old, "new": new}}
            for session_id, (old, new) in start_times.items()
        },
        sessions_by_change_key={
            session_id: {
                "id": session_id,
                "start_time": new,
                "duration": 2,
                "weekday": "monday",
                "week": "2026-01-05",
                "classes": [session_id],
            }
            for session_id, (_old, new) in start_times.items()
        },
        dependency_graph=dependency_graph,
    )


def test_exact_time_swap_is_classified_as_exchange() -> None:
    graph = _swap_graph({"a": (830, 1000), "b": (1000, 830)})
    assert graph.get_graph_ordered_modifications() == [("a", "exchange"), ("b", "exchange")]


def test_offset_time_cycle_is_classified_as_move() -> None:
    graph = _swap_graph({"a": (830, 1030), "b": (1000, 830)})
    assert graph.get_graph_ordered_modifications() == [("a", "move"), ("b", "move")]


def test_is_exact_time_exchange_false_for_single_session_group() -> None:
    graph = _swap_graph({"a": (830, 1000), "b": (1000, 830)})
    assert graph.is_exact_time_exchange(["a"]) is False


def test_is_exact_time_exchange_false_when_session_missing_from_snapshots() -> None:
    graph = _swap_graph({"a": (830, 1000), "b": (1000, 830)})
    graph.sessions_by_change_key.pop("b")
    assert graph.is_exact_time_exchange(["a", "b"]) is False


def test_time_placement_key_is_comparable_tuple() -> None:
    placement = TimePlacement(time_slots=(510, 540), weekday="monday", week="2026-01-05")
    assert ExportGraph.time_placement_key(placement) == ((510, 540), "monday", "2026-01-05")


# ---------------------------------------------------------------------------
# -- week range
# ---------------------------------------------------------------------------


def test_build_week_range_contiguous_weeks() -> None:
    weeks = ["2026-01-05", "2026-01-12", "2026-01-19"]
    assert ExportGraph.build_week_range(weeks) == {
        "start": "2026-01-05",
        "end": "2026-01-19",
        "contiguous": True,
    }


def test_build_week_range_non_contiguous_weeks() -> None:
    weeks = ["2026-01-05", "2026-01-19"]
    result = ExportGraph.build_week_range(weeks)
    assert result["start"] == "2026-01-05"
    assert result["end"] == "2026-01-19"
    assert result["contiguous"] is False


def test_build_week_range_single_week_is_contiguous() -> None:
    result = ExportGraph.build_week_range(["2026-01-05"])
    assert result == {"start": "2026-01-05", "end": "2026-01-05", "contiguous": True}


def test_build_week_range_dedupes_and_sorts_weeks() -> None:
    weeks = ["2026-01-12", "2026-01-05", "2026-01-12"]
    result = ExportGraph.build_week_range(weeks)
    assert result["start"] == "2026-01-05"
    assert result["end"] == "2026-01-12"
    assert result["contiguous"] is True


def test_build_week_range_accepts_date_objects() -> None:
    weeks = [datetime.date(2026, 1, 5), datetime.date(2026, 1, 12)]
    result = ExportGraph.build_week_range(weeks)
    assert result["start"] == "2026-01-05"
    assert result["contiguous"] is True


def test_build_week_range_empty_when_no_parseable_weeks() -> None:
    assert ExportGraph.build_week_range(["not-a-date", None]) == {
        "start": None,
        "end": None,
        "contiguous": False,
    }


# ---------------------------------------------------------------------------
# -- groupable_changes
# ---------------------------------------------------------------------------


def test_groupable_changes_drops_week_field() -> None:
    changes = {
        "week": {"old": "2026-01-05", "new": "2026-01-12"},
        "start_time": {"old": 830, "new": 1000},
    }
    assert ExportGraph.groupable_changes(changes) == {"start_time": {"old": 830, "new": 1000}}


def test_groupable_changes_leaves_non_week_changes_untouched() -> None:
    changes = {"start_time": {"old": 830, "new": 1000}}
    assert ExportGraph.groupable_changes(changes) == changes


# ---------------------------------------------------------------------------
# -- session snapshot & class helpers
# ---------------------------------------------------------------------------


def _snapshot(session_id: str, **overrides: object) -> dict:
    base = {
        "id": session_id,
        "original_block_id": "block",
        "start_time": 830,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
        "room_ids": ("r1",),
        "teacher_ids": ("t1",),
        "class_ids": ("c1",),
        "rooms": ["B101"],
        "teachers": (),
        "classes": ["1LEIC01"],
        "subjects": (),
    }
    base.update(overrides)
    return base


def test_get_public_session_data_strips_graph_only_id_fields() -> None:
    graph = make_graph(initial_sessions={"s1": _snapshot("s1")})

    public = graph.get_public_session_data("s1")

    assert "room_ids" not in public
    assert "teacher_ids" not in public
    assert "class_ids" not in public
    assert public["id"] == "s1"
    assert public["rooms"] == ["B101"]
    assert public["classes"] == ["1LEIC01"]


def test_get_session_classes_sorted_string_tuple() -> None:
    graph = make_graph(
        sessions_by_change_key={"s1": {"classes": ["1LEIC02", "1LEIC01"]}},
    )
    assert graph.get_session_classes("s1") == ("1LEIC01", "1LEIC02")


def test_get_session_classes_empty_for_unknown_session() -> None:
    graph = make_graph(sessions_by_change_key={})
    assert graph.get_session_classes("missing") == ()


def test_get_group_classes_unions_across_sessions() -> None:
    graph = make_graph(
        sessions_by_change_key={
            "s1": {"classes": ["X"]},
            "s2": {"classes": ["Y", "X"]},
        },
    )
    assert graph.get_group_classes(["s1", "s2"]) == ("X", "Y")


def test_sort_group_by_classes_orders_by_classes_then_id() -> None:
    graph = make_graph(
        sessions_by_change_key={
            "s2": {"classes": ["X"]},
            "s1": {"classes": ["X"]},
            "s3": {"classes": ["Y"]},
        },
    )
    assert graph.sort_group_by_classes({"s1", "s2", "s3"}) == ["s1", "s2", "s3"]


# ---------------------------------------------------------------------------
# -- original block weeks
# ---------------------------------------------------------------------------


def test_get_original_block_weeks_uses_preloaded_map() -> None:
    graph = make_graph(
        original_block_weeks={"block": ["2026-01-05", "2026-01-12"]},
        initial_sessions={},
    )
    assert graph.get_original_block_weeks("block") == ["2026-01-05", "2026-01-12"]


def test_get_original_block_weeks_falls_back_to_initial_sessions() -> None:
    graph = make_graph(
        original_block_weeks={},
        initial_sessions={
            "a": {"id": "a", "original_block_id": "block", "week": "2026-01-05"},
            "b": {"id": "b", "original_block_id": "block", "week": "2026-01-12"},
            "c": {"id": "c", "original_block_id": "other", "week": "2026-01-05"},
        },
    )
    assert graph.get_original_block_weeks("block") == ["2026-01-05", "2026-01-12"]


# ---------------------------------------------------------------------------
# -- sort_session_ids_by_week / build_group_modifications
# ---------------------------------------------------------------------------


def test_sort_session_ids_by_week_orders_by_public_week() -> None:
    graph = make_graph(
        initial_sessions={
            "a": _snapshot("a", week="2026-01-12"),
            "b": _snapshot("b", week="2026-01-05"),
        },
    )
    assert graph.sort_session_ids_by_week(["a", "b"]) == ["b", "a"]


def test_build_group_modifications_returns_single_session_changes_verbatim() -> None:
    changes = {"a": {"start_time": {"old": 830, "new": 1000}}}
    graph = make_graph(changes=changes)
    assert graph.build_group_modifications(["a"]) == changes["a"]


def test_build_group_modifications_drops_week_for_recurring_group() -> None:
    changes = {
        "a": {
            "week": {"old": "2026-01-05", "new": "2026-01-12"},
            "start_time": {"old": 830, "new": 1000},
        },
    }
    graph = make_graph(changes=changes)
    assert graph.build_group_modifications(["a", "b"]) == {
        "start_time": {"old": 830, "new": 1000},
    }


# ---------------------------------------------------------------------------
# -- build_modification_steps (table-ordered path, no dependency graph)
# ---------------------------------------------------------------------------


def test_build_modification_steps_single_move_step() -> None:
    changes = {"a": {"start_time": {"old": 830, "new": 1000}}}
    graph = make_graph(
        changes=changes,
        initial_sessions={"a": _snapshot("a", original_block_id="block")},
        original_block_weeks={"block": ["2026-01-05"]},
    )

    steps = graph.build_modification_steps([("a", "move")])

    assert len(steps) == 1
    step = steps[0]
    assert step["type"] == "move"
    assert step["session_ids"] == ["a"]
    # ``modifications`` is re-serialized through ExportSessionModifications, so
    # the changed column is present and every other declared column is None.
    assert step["modifications"]["start_time"] == {"old": 830, "new": 1000}
    assert step["modifications"]["week"] is None
    assert step["modifications"]["rooms"] is None
    assert step["dependencies"] == []
    assert step["applies_to_all_weeks"] is True
    assert step["week_range"] == {
        "start": "2026-01-05",
        "end": "2026-01-05",
        "contiguous": True,
    }


def test_build_modification_steps_groups_recurring_block_across_weeks() -> None:
    changes = {
        "a": {"start_time": {"old": 830, "new": 1000}},
        "b": {"start_time": {"old": 830, "new": 1000}},
    }
    graph = make_graph(
        changes=changes,
        initial_sessions={
            "a": _snapshot("a", original_block_id="block", week="2026-01-05"),
            "b": _snapshot("b", original_block_id="block", week="2026-01-12"),
        },
        original_block_weeks={"block": ["2026-01-05", "2026-01-12"]},
    )

    steps = graph.build_modification_steps([("a", "move"), ("b", "move")])

    # Same block + same groupable change -> one grouped step across both weeks.
    assert len(steps) == 1
    step = steps[0]
    assert step["session_ids"] == ["a", "b"]
    assert step["weeks"] == ["2026-01-05", "2026-01-12"]
    assert step["applies_to_all_weeks"] is True
    assert step["week_range"]["contiguous"] is True


def test_build_modification_steps_partial_block_is_not_all_weeks() -> None:
    changes = {"a": {"start_time": {"old": 830, "new": 1000}}}
    graph = make_graph(
        changes=changes,
        initial_sessions={"a": _snapshot("a", original_block_id="block", week="2026-01-05")},
        original_block_weeks={"block": ["2026-01-05", "2026-01-12"]},
    )

    steps = graph.build_modification_steps([("a", "move")])

    assert steps[0]["applies_to_all_weeks"] is False


def test_build_modification_steps_distinct_changes_stay_separate() -> None:
    changes = {
        "a": {"start_time": {"old": 830, "new": 1000}},
        "b": {"start_time": {"old": 900, "new": 1100}},
    }
    graph = make_graph(
        changes=changes,
        initial_sessions={
            "a": _snapshot("a", original_block_id="block-a", week="2026-01-05"),
            "b": _snapshot("b", original_block_id="block-b", week="2026-01-05"),
        },
        original_block_weeks={"block-a": ["2026-01-05"], "block-b": ["2026-01-05"]},
    )

    steps = graph.build_modification_steps([("a", "move"), ("b", "move")])

    assert len(steps) == 2
    assert {tuple(step["session_ids"]) for step in steps} == {("a",), ("b",)}


def test_build_modification_steps_exchange_type_wins_within_group() -> None:
    changes = {"a": {"start_time": {"old": 830, "new": 1000}}}
    graph = make_graph(
        changes=changes,
        initial_sessions={"a": _snapshot("a", original_block_id="block")},
        original_block_weeks={"block": ["2026-01-05"]},
    )

    steps = graph.build_modification_steps([("a", "exchange")])

    assert steps[0]["type"] == "exchange"
