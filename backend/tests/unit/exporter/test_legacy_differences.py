"""Unit tests for :class:`src.exporter.legacy.differences.Comparator`.

``build_order_graph`` is the legacy sequential ordering algorithm: it emits a
conflict-free order for a set of moved sessions, or raises when no such order
exists (a true swap forms a cycle; two sessions colliding only in their final
positions have no safe final order). It is exercised here without a database by
building an uninitialized ``Comparator`` and passing session maps directly.
"""

import networkx as nx
from pytest import raises

from src.exporter.legacy.differences import Comparator


def make_comparator() -> Comparator:
    return Comparator.__new__(Comparator)


def sess(
    *,
    start_time: int,
    duration: int = 2,
    week: str = "2026-01-05",
    weekday: str = "monday",
    room_ids: tuple[str, ...] = (),
    teacher_ids: tuple[str, ...] = (),
    class_subjects: dict[str, str] | None = None,
) -> dict:
    return {
        "week": week,
        "weekday": weekday,
        "start_time": start_time,
        "duration": duration,
        "room_ids": list(room_ids),
        "teacher_ids": list(teacher_ids),
        "class_subjects": class_subjects or {},
    }


# ---------------------------------------------------------------------------
# -- No / independent changes
# ---------------------------------------------------------------------------


def test_build_order_graph_returns_empty_when_nothing_changed() -> None:
    comparator = make_comparator()
    old_map = {"a": sess(start_time=830, room_ids=("R1",))}
    new_map = {"a": sess(start_time=830, room_ids=("R1",))}

    assert comparator.build_order_graph(old_map, new_map) == ()


def test_build_order_graph_orders_independent_changes_deterministically() -> None:
    comparator = make_comparator()
    old_map = {
        "a": sess(start_time=830, room_ids=("R1",)),
        "b": sess(start_time=830, room_ids=("R2",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R2",)),
    }

    order = comparator.build_order_graph(old_map, new_map)

    # No conflicts between them: both appear, in sorted id order.
    assert set(order) == {"a", "b"}
    assert order == ("a", "b")


# ---------------------------------------------------------------------------
# -- Directed prerequisite (one must move before the other)
# ---------------------------------------------------------------------------


def test_build_order_graph_orders_blocker_before_mover() -> None:
    comparator = make_comparator()
    # A moves into the slot B currently occupies (share R1), so B must move
    # first. B only changes room (stays at 1000), so it has a safe new slot.
    old_map = {
        "a": sess(start_time=830, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R1",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R2",)),
    }

    order = comparator.build_order_graph(old_map, new_map)

    assert order == ("b", "a")


# ---------------------------------------------------------------------------
# -- Unsolvable orderings
# ---------------------------------------------------------------------------


def test_build_order_graph_raises_when_final_positions_conflict() -> None:
    comparator = make_comparator()
    # Both move into the same final slot sharing R1, without conflicting before:
    # there is no conflict-free final state at all.
    old_map = {
        "a": sess(start_time=800, room_ids=("R1",)),
        "b": sess(start_time=900, room_ids=("R1",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R1",)),
    }

    with raises(ValueError, match="No conflict-free final order"):
        comparator.build_order_graph(old_map, new_map)


def test_build_order_graph_raises_on_swap_cycle() -> None:
    comparator = make_comparator()
    # A classic exchange: A and B swap start times in the same room. Each move
    # collides with the other's current position -> a 2-cycle with no order.
    old_map = {
        "a": sess(start_time=800, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R1",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=800, room_ids=("R1",)),
    }

    with raises(ValueError, match="No conflict-free sequential order"):
        comparator.build_order_graph(old_map, new_map)


# ---------------------------------------------------------------------------
# -- Explicit changed-id restriction
# ---------------------------------------------------------------------------


def test_build_order_graph_honors_explicit_changed_ids() -> None:
    comparator = make_comparator()
    old_map = {
        "a": sess(start_time=830, room_ids=("R1",)),
        "b": sess(start_time=1100, room_ids=("R2",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=1200, room_ids=("R2",)),
    }

    # Only "a" is considered even though "b" also changed.
    order = comparator.build_order_graph(old_map, new_map, changed_ids=["a"])
    assert order == ("a",)


def test_build_order_graph_ignores_changed_ids_missing_from_maps() -> None:
    comparator = make_comparator()
    old_map = {"a": sess(start_time=830, room_ids=("R1",))}
    new_map = {"a": sess(start_time=1000, room_ids=("R1",))}

    order = comparator.build_order_graph(old_map, new_map, changed_ids=["a", "ghost"])
    assert order == ("a",)


def test_build_order_graph_returns_topologically_valid_order() -> None:
    comparator = make_comparator()
    old_map = {
        "a": sess(start_time=830, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R1",)),
    }
    new_map = {
        "a": sess(start_time=1000, room_ids=("R1",)),
        "b": sess(start_time=1000, room_ids=("R2",)),
    }

    order = comparator.build_order_graph(old_map, new_map)

    # Reconstruct the emitted dependency: b precedes a.
    assert list(order).index("b") < list(order).index("a")
    # And it is a genuine topological order of a DAG.
    graph = nx.DiGraph()
    graph.add_nodes_from(order)
    assert nx.is_directed_acyclic_graph(graph)
