"""Unit tests for :mod:`src.exporter.export_graph_types`.

The frozen dataclasses that model a session's movement through the resource
graph. The subtle piece is :meth:`ResourceMovement.pairs`, which decides which
``(old_resource, new_resource)`` edges a change produces — the shape of that
output drives every dependency edge the exporter later builds.
"""

import datetime

from pytest import mark

from src.exporter.export_graph_types import (
    RESOURCE_SPECS,
    ResourceMovement,
    ResourceSpec,
    TimeMovement,
    TimePlacement,
)
from src.projects.projects_db.schemas.weekday import WeekDay

# ---------------------------------------------------------------------------
# -- TimePlacement
# ---------------------------------------------------------------------------


def test_time_placement_node_stringifies_weekday_and_week() -> None:
    placement = TimePlacement(
        time_slots=(510, 540),
        weekday=WeekDay.MONDAY,
        week=datetime.date(2026, 1, 5),
    )
    assert placement.node("room-1", 510) == ("room-1", 510, "monday", "2026-01-05")


def test_time_placement_node_accepts_already_stringified_coordinates() -> None:
    placement = TimePlacement(time_slots=(510,), weekday="monday", week="2026-01-05")
    assert placement.node(42, 510) == (42, 510, "monday", "2026-01-05")


def test_time_placement_is_hashable_and_frozen() -> None:
    placement = TimePlacement(time_slots=(510, 540), weekday="monday", week="2026-01-05")
    # Frozen dataclasses are hashable, so placements can key dicts/sets.
    assert placement in {placement}


# ---------------------------------------------------------------------------
# -- TimeMovement
# ---------------------------------------------------------------------------


def test_time_movement_carries_old_new_and_changed_flag() -> None:
    old = TimePlacement(time_slots=(510, 540), weekday="monday", week="2026-01-05")
    new = TimePlacement(time_slots=(600, 630), weekday="monday", week="2026-01-05")
    movement = TimeMovement(old=old, new=new, changed=True)
    assert movement.old is old
    assert movement.new is new
    assert movement.changed is True


# ---------------------------------------------------------------------------
# -- ResourceMovement.changed
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("old", "new", "expected"),
    [
        ((), (), False),
        (("a",), ("a",), False),
        (("a", "b"), ("b", "a"), False),  # order-insensitive
        (("a", "a"), ("a",), False),  # duplicate-insensitive
        (("a",), ("b",), True),
        (("a",), (), True),
        ((), ("a",), True),
        (("a", "b"), ("a",), True),
    ],
)
def test_resource_movement_changed_compares_as_sets(
    old: tuple[str, ...],
    new: tuple[str, ...],
    expected: bool,
) -> None:
    assert ResourceMovement(old=old, new=new).changed is expected


# ---------------------------------------------------------------------------
# -- ResourceMovement.pairs
# ---------------------------------------------------------------------------


def test_pairs_empty_when_either_side_is_empty() -> None:
    assert ResourceMovement(old=(), new=("a",)).pairs(include_shared=True) == []
    assert ResourceMovement(old=("a",), new=()).pairs(include_shared=False) == []


def test_pairs_identity_when_resource_sets_equal() -> None:
    movement = ResourceMovement(old=("b", "a"), new=("a", "b"))
    # Equal sets -> each resource is paired with itself, sorted by str.
    assert movement.pairs(include_shared=True) == [("a", "a"), ("b", "b")]
    assert movement.pairs(include_shared=False) == [("a", "a"), ("b", "b")]


def test_pairs_dedupes_repeated_resources_in_identity_case() -> None:
    movement = ResourceMovement(old=("a", "a"), new=("a",))
    assert movement.pairs(include_shared=True) == [("a", "a")]


def test_pairs_full_swap_maps_removed_to_added() -> None:
    movement = ResourceMovement(old=("a",), new=("b",))
    assert movement.pairs(include_shared=False) == [("a", "b")]


def test_pairs_removed_and_added_is_cartesian_product() -> None:
    movement = ResourceMovement(old=("a", "b"), new=("c", "d"))
    # removed={a,b} x added={c,d}
    assert movement.pairs(include_shared=False) == [
        ("a", "c"),
        ("a", "d"),
        ("b", "c"),
        ("b", "d"),
    ]


def test_pairs_partial_swap_includes_shared_only_when_requested() -> None:
    movement = ResourceMovement(old=("a", "b"), new=("a", "c"))
    # shared={a}, removed={b}, added={c}
    assert movement.pairs(include_shared=True) == [("a", "a"), ("b", "c")]
    assert movement.pairs(include_shared=False) == [("b", "c")]


def test_pairs_pure_addition_connects_shared_to_added() -> None:
    movement = ResourceMovement(old=("a",), new=("a", "b"))
    # No removals: the added resource is reached from every shared one.
    assert movement.pairs(include_shared=False) == [("a", "b")]


def test_pairs_pure_addition_with_shared_prepends_identity_edges() -> None:
    movement = ResourceMovement(old=("a",), new=("a", "b"))
    assert movement.pairs(include_shared=True) == [("a", "a"), ("a", "b")]


def test_pairs_pure_removal_connects_removed_to_shared() -> None:
    movement = ResourceMovement(old=("a", "b"), new=("a",))
    # No additions: the removed resource points at every surviving (shared) one.
    assert movement.pairs(include_shared=False) == [("b", "a")]


def test_pairs_pure_removal_with_shared_prepends_identity_edges() -> None:
    movement = ResourceMovement(old=("a", "b"), new=("a",))
    assert movement.pairs(include_shared=True) == [("a", "a"), ("b", "a")]


def test_pairs_sorts_resources_by_string_form() -> None:
    # Numeric resources are ordered by their string representation.
    movement = ResourceMovement(old=(10, 2), new=(10, 2))
    assert movement.pairs(include_shared=True) == [(10, 10), (2, 2)]


# ---------------------------------------------------------------------------
# -- ResourceSpec / RESOURCE_SPECS
# ---------------------------------------------------------------------------


def test_resource_specs_cover_rooms_teachers_and_classes() -> None:
    by_name = {spec.graph_name: spec for spec in RESOURCE_SPECS}
    assert set(by_name) == {"rooms", "teachers", "classes"}


@mark.parametrize(
    ("graph_name", "session_field", "relation_field", "id_key"),
    [
        ("rooms", "room_ids", "rooms", "room_id"),
        ("teachers", "teacher_ids", "teachers", "teacher_id"),
        ("classes", "class_ids", "class_subjects", "class_id"),
    ],
)
def test_resource_spec_field_wiring(
    graph_name: str,
    session_field: str,
    relation_field: str,
    id_key: str,
) -> None:
    spec = next(s for s in RESOURCE_SPECS if s.graph_name == graph_name)
    assert spec == ResourceSpec(graph_name, session_field, relation_field, id_key)
