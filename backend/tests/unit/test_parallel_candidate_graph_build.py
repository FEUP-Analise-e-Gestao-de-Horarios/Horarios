"""Pure unit tests for ``build_candidate_components`` (and, through it, the two
``_component_uuid`` behaviors that surface as ``candidate_group_id``).

No database, HTTP, or fixtures: the function is fed hand-built slot rows and its
returned components are inspected directly. Result order is non-deterministic
(components come from dict iteration over subjects/roots), so every assertion
indexes by ``candidate_group_id`` or ``frozenset(block_ids)`` — never by
position.

Standalone helper units (``_component_uuid`` in isolation, ``_UnionFind``,
``CandidateComponent.is_connected_subset``) live in
``test_parallel_candidate_graph_helpers.py``; this file owns only
``build_candidate_components``.
"""

import dataclasses
import random
import uuid
from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations

import pytest

from src.projects.projects_db.dao.parallel_candidate_graph import (
    CandidateComponent,
    CandidateEdge,
    CandidateSlotRow,
    build_candidate_components,
)
from src.projects.projects_db.schemas.weekday import WeekDay

# Fixed block ids so assertions can name them and rely on their ordering.
A = uuid.UUID(int=1)
B = uuid.UUID(int=2)
C = uuid.UUID(int=3)
D = uuid.UUID(int=4)
# A high/low pair to exercise canonical edge ordering independent of insertion.
B_LO = uuid.UUID(int=1)
B_HI = uuid.UUID(int=9)

# Two subjects.
S1 = uuid.UUID(int=100)
S2 = uuid.UUID(int=200)

# Distinct weeks that share the same (weekday, start_time).
W1 = date(2025, 9, 15)
W2 = date(2025, 9, 22)
W3 = date(2025, 9, 29)


def row(
    week: date,
    weekday: WeekDay,
    start_time: int,
    subject_id: uuid.UUID,
    block_id: uuid.UUID,
) -> CandidateSlotRow:
    """Build a single ``(week, weekday, start_time, subject_id, block_id)`` row."""
    return (week, weekday, start_time, subject_id, block_id)


def _by_blocks(
    components: list[CandidateComponent],
) -> dict[frozenset[uuid.UUID], CandidateComponent]:
    """Index components by their (unique) block-id membership."""
    index = {component.block_ids: component for component in components}
    assert len(index) == len(components), "block_ids collided; index would drop components"
    return index


def _by_group_id(
    components: list[CandidateComponent],
) -> dict[uuid.UUID, CandidateComponent]:
    """Index components by their ``candidate_group_id``."""
    index = {component.candidate_group_id: component for component in components}
    assert len(index) == len(components), "candidate_group_id collided"
    return index


def _expected_group_id(subject_id: uuid.UUID, *block_ids: uuid.UUID) -> uuid.UUID:
    """Recompute the golden component id independently of the module helper."""
    members = ",".join(str(block_id) for block_id in sorted(block_ids))
    return uuid.uuid5(uuid.NAMESPACE_OID, f"{subject_id}:{members}")


# --------------------------------------------------------------------------- #
# Empty / trivial inputs
# --------------------------------------------------------------------------- #


def test_empty_input_yields_empty_list() -> None:
    """No rows -> no components (subsumes the smoke empty test)."""
    assert build_candidate_components([]) == []


def test_single_block_single_slot_forms_nothing() -> None:
    """A lone block at one slot has no partner, so no node/edge/component."""
    rows = [row(W1, WeekDay.MONDAY, 9, S1, A)]
    assert build_candidate_components(rows) == []


def test_eligible_solo_block_across_many_weeks_produces_nothing() -> None:
    """Same (weekday, start_time) on several weeks keeps A eligible but partnerless."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W2, WeekDay.MONDAY, 9, S1, A),
    ]
    assert build_candidate_components(rows) == []


# --------------------------------------------------------------------------- #
# Two blocks sharing a slot: the base case and its variations
# --------------------------------------------------------------------------- #


def test_two_blocks_one_slot_single_component_one_edge() -> None:
    """Two blocks on one slot => one component, one edge, one week, golden id."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.subject_id == S1
    assert component.block_ids == frozenset({A, B})
    assert component.edges == (CandidateEdge(A, B, (W1,)),)
    assert component.candidate_group_id == _expected_group_id(S1, A, B)


@pytest.mark.parametrize("swap", [False, True])
def test_edge_endpoints_canonical_regardless_of_insertion_order(swap: bool) -> None:
    """Edge stores block_a < block_b whatever order the rows arrive in."""
    high = row(W1, WeekDay.MONDAY, 9, S1, B_HI)
    low = row(W1, WeekDay.MONDAY, 9, S1, B_LO)
    rows = [low, high] if swap else [high, low]

    components = build_candidate_components(rows)

    assert len(components) == 1
    (edge,) = components[0].edges
    assert edge.block_a == B_LO
    assert edge.block_b == B_HI
    assert edge.weeks == (W1,)


def test_pair_colliding_on_multiple_weeks_aggregates_sorted_weeks() -> None:
    """Weeks fed out of order collapse onto one edge, sorted ascending."""
    rows = [
        row(W3, WeekDay.MONDAY, 9, S1, A),
        row(W3, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W2, WeekDay.MONDAY, 9, S1, A),
        row(W2, WeekDay.MONDAY, 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    (edge,) = components[0].edges
    assert edge.weeks == (W1, W2, W3)


def test_edge_weeks_exclude_week_where_only_one_block_present() -> None:
    """A week where only one of the pair is present is NOT on the edge.

    A is at (MONDAY,9) on all three weeks; B only on W1 and W3. Both stay
    eligible (each spans a single (weekday,start_time) slot), but they only
    share a slot on W1 and W3, so the edge must carry (W1, W3) -- never W2.
    """
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W2, WeekDay.MONDAY, 9, S1, A),
        row(W3, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W3, WeekDay.MONDAY, 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    assert components[0].block_ids == frozenset({A, B})
    (edge,) = components[0].edges
    assert edge.weeks == (W1, W3)


@pytest.mark.parametrize(
    ("weeks", "expected"),
    [
        ([W1], (W1,)),
        ([W1, W2, W3], (W1, W2, W3)),
    ],
)
def test_shared_weeks_connect_and_are_reported_sorted(
    weeks: list[date],
    expected: tuple[date, ...],
) -> None:
    """One shared week is enough; more weeks all land on the single edge."""
    rows: list[CandidateSlotRow] = []
    for week in weeks:
        rows.append(row(week, WeekDay.MONDAY, 9, S1, A))
        rows.append(row(week, WeekDay.MONDAY, 9, S1, B))

    components = build_candidate_components(rows)

    assert len(components) == 1
    (edge,) = components[0].edges
    assert edge.weeks == expected


def test_same_slot_across_many_weeks_stays_eligible() -> None:
    """A,B both at (MONDAY,9) on three weeks: one component, three-week edge."""
    rows: list[CandidateSlotRow] = []
    for week in (W1, W2, W3):
        rows.append(row(week, WeekDay.MONDAY, 9, S1, A))
        rows.append(row(week, WeekDay.MONDAY, 9, S1, B))

    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({A, B})
    assert component.edges == (CandidateEdge(A, B, (W1, W2, W3)),)


def test_duplicate_rows_collapse_to_one_edge_one_week() -> None:
    """Exact-duplicate rows are idempotent: one edge, one week."""
    single = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    rows = single * 3
    components = build_candidate_components(rows)

    assert len(components) == 1
    assert components[0].edges == (CandidateEdge(A, B, (W1,)),)


# --------------------------------------------------------------------------- #
# Heterogeneous (multi-slot) blocks are dropped
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "second_slot",
    [
        (WeekDay.TUESDAY, 9),  # differs by weekday
        (WeekDay.MONDAY, 11),  # differs by start_time
    ],
)
def test_heterogeneous_block_dropped_partner_unpartnered(
    second_slot: tuple[WeekDay, int],
) -> None:
    """B1 spanning two distinct (weekday,start_time) slots is dropped entirely.

    Its Monday partner B2 is then alone in that slot and forms nothing.
    """
    other_weekday, other_start = second_slot
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, other_weekday, other_start, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    assert build_candidate_components(rows) == []


def test_eligibility_drop_discards_a_real_multiweek_partnership() -> None:
    """A block that genuinely partners B on some weeks is still dropped whole
    once it also appears at a *different* slot on another week.

    A collides with B at (MONDAY,9) on W1 and W3 -- a real partnership -- but on
    W2 A moves to (TUESDAY,9). A therefore spans two distinct (weekday,start_time)
    slots and is dropped entirely (the eligibility check keys on slot, ignoring
    week), leaving B partnerless. The W1/W3 collision is discarded, not salvaged.
    """
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W3, WeekDay.MONDAY, 9, S1, A),
        row(W2, WeekDay.TUESDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W3, WeekDay.MONDAY, 9, S1, B),
    ]
    assert build_candidate_components(rows) == []


def test_eligibility_ignores_subject_when_counting_slots() -> None:
    """Slot-count eligibility keys on (weekday,start_time) only, not subject.

    A has one slot per subject but two distinct (weekday,start_time) slots
    overall, so it is dropped from both subjects, leaving B and C partnerless.
    """
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.TUESDAY, 9, S2, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.TUESDAY, 9, S2, C),
    ]
    assert build_candidate_components(rows) == []


# --------------------------------------------------------------------------- #
# Multi-subject behavior
# --------------------------------------------------------------------------- #


def test_multi_subject_block_appears_once_per_subject_no_bridge() -> None:
    """A single-slot block under two subjects yields one component per subject."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 9, S2, A),
        row(W1, WeekDay.MONDAY, 9, S2, C),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 2
    by_blocks = _by_blocks(components)
    s1 = by_blocks[frozenset({A, B})]
    s2 = by_blocks[frozenset({A, C})]

    assert s1.subject_id == S1
    assert s2.subject_id == S2
    assert s1.candidate_group_id != s2.candidate_group_id
    assert s1.candidate_group_id == _expected_group_id(S1, A, B)
    assert s2.candidate_group_id == _expected_group_id(S2, A, C)


def test_per_subject_edge_weeks_not_merged_across_subjects() -> None:
    """The same pair colliding under two subjects keeps each subject's weeks apart."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W2, WeekDay.MONDAY, 9, S2, A),
        row(W2, WeekDay.MONDAY, 9, S2, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 2
    by_group = _by_group_id(components)
    s1 = by_group[_expected_group_id(S1, A, B)]
    s2 = by_group[_expected_group_id(S2, A, B)]

    assert s1.edges == (CandidateEdge(A, B, (W1,)),)
    assert s2.edges == (CandidateEdge(A, B, (W2,)),)


def test_same_time_different_subjects_do_not_collide() -> None:
    """Slot key includes subject_id: two blocks at the same time but different
    subjects never share a slot and so never form a component."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S2, B),
    ]
    assert build_candidate_components(rows) == []


# --------------------------------------------------------------------------- #
# Chains: the transitive-connector trap
# --------------------------------------------------------------------------- #


def test_naive_chain_via_two_distinct_slots_drops_connector() -> None:
    """A-B at (MONDAY,9) and B-C at (MONDAY,11): B spans two slots and is dropped,
    so neither pair survives and nothing is returned."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 11, S1, B),
        row(W1, WeekDay.MONDAY, 11, S1, C),
    ]
    assert build_candidate_components(rows) == []


def test_transitive_chain_same_slot_different_weeks_merges_three_blocks() -> None:
    """Same (MONDAY,9) slot: w1 pairs A-B, w2 pairs B-C. B stays homogeneous, so
    the union-find merges {A,B,C} with edges A-B(w1) and B-C(w2), no A-C."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W2, WeekDay.MONDAY, 9, S1, B),
        row(W2, WeekDay.MONDAY, 9, S1, C),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({A, B, C})
    assert component.edges == (
        CandidateEdge(A, B, (W1,)),
        CandidateEdge(B, C, (W2,)),
    )


def test_block_partners_with_different_blocks_across_weeks_same_slot() -> None:
    """A at (MONDAY,9) pairs B (w1), C (w2), D (w3): a star component around A."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W2, WeekDay.MONDAY, 9, S1, A),
        row(W2, WeekDay.MONDAY, 9, S1, C),
        row(W3, WeekDay.MONDAY, 9, S1, A),
        row(W3, WeekDay.MONDAY, 9, S1, D),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({A, B, C, D})
    assert component.edges == (
        CandidateEdge(A, B, (W1,)),
        CandidateEdge(A, C, (W2,)),
        CandidateEdge(A, D, (W3,)),
    )


# --------------------------------------------------------------------------- #
# Triangles, disjoint components, edge ordering
# --------------------------------------------------------------------------- #


def test_three_blocks_one_slot_form_triangle() -> None:
    """Three blocks on one slot are mutually adjacent: three edges, one component."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 9, S1, C),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({A, B, C})
    assert component.edges == (
        CandidateEdge(A, B, (W1,)),
        CandidateEdge(A, C, (W1,)),
        CandidateEdge(B, C, (W1,)),
    )


def test_edges_within_component_sorted_by_endpoints_scrambled_input() -> None:
    """Edges come out sorted by (block_a, block_b) even from scrambled rows."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, C),
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    assert components[0].edges == (
        CandidateEdge(A, B, (W1,)),
        CandidateEdge(A, C, (W1,)),
        CandidateEdge(B, C, (W1,)),
    )


def test_two_disjoint_components_under_same_subject() -> None:
    """Two non-overlapping slots for one subject yield two separate components."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.TUESDAY, 9, S1, C),
        row(W1, WeekDay.TUESDAY, 9, S1, D),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 2
    by_blocks = _by_blocks(components)
    ab = by_blocks[frozenset({A, B})]
    cd = by_blocks[frozenset({C, D})]

    assert ab.subject_id == S1
    assert cd.subject_id == S1
    assert ab.candidate_group_id != cd.candidate_group_id
    assert ab.edges == (CandidateEdge(A, B, (W1,)),)
    assert cd.edges == (CandidateEdge(C, D, (W1,)),)


# --------------------------------------------------------------------------- #
# candidate_group_id determinism / sensitivity (through build)
# --------------------------------------------------------------------------- #


def test_candidate_group_id_deterministic_across_runs() -> None:
    """Building the same {A,B}/S1 component twice yields the same id, matching uuid5."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    first = build_candidate_components(rows)
    second = build_candidate_components(list(rows))

    assert len(first) == 1
    assert len(second) == 1
    expected = _expected_group_id(S1, A, B)
    assert first[0].candidate_group_id == expected
    assert second[0].candidate_group_id == expected


def test_candidate_group_id_changes_when_membership_changes() -> None:
    """Adding C to the {A,B} slot changes the component's id (same subject)."""
    pair_rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    trio_rows = [*pair_rows, row(W1, WeekDay.MONDAY, 9, S1, C)]

    pair = build_candidate_components(pair_rows)
    trio = build_candidate_components(trio_rows)

    assert len(pair) == 1
    assert len(trio) == 1
    assert pair[0].block_ids == frozenset({A, B})
    assert trio[0].block_ids == frozenset({A, B, C})
    assert pair[0].candidate_group_id != trio[0].candidate_group_id
    assert pair[0].candidate_group_id == _expected_group_id(S1, A, B)
    assert trio[0].candidate_group_id == _expected_group_id(S1, A, B, C)


# --------------------------------------------------------------------------- #
# WeekDay alias equality
# --------------------------------------------------------------------------- #


def test_weekday_pt_and_en_aliases_share_slot() -> None:
    """WeekDay('segunda') and WeekDay('monday') are both MONDAY, so blocks
    constructed either way land in the same slot and form a component."""
    assert WeekDay("segunda") is WeekDay.MONDAY
    assert WeekDay("monday") is WeekDay.MONDAY

    rows = [
        row(W1, WeekDay("segunda"), 9, S1, A),
        row(W1, WeekDay("monday"), 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    assert components[0].block_ids == frozenset({A, B})
    assert components[0].edges == (CandidateEdge(A, B, (W1,)),)


# --------------------------------------------------------------------------- #
# Larger combined topology
# --------------------------------------------------------------------------- #


def test_large_topology_two_subjects_chains_triangles_and_orphans() -> None:
    """A combined graph exercises chains, triangles, disjoint groups, cross-subject
    reuse of a block, and dropped heterogeneous/orphan blocks at once."""
    # Extra fixed ids for the larger scenario.
    e = uuid.UUID(int=5)
    f = uuid.UUID(int=6)
    g = uuid.UUID(int=7)
    h = uuid.UUID(int=8)
    i = uuid.UUID(int=10)

    rows = [
        # S1 slot (MONDAY,9): w1 triangle {A,B,C}, w2 pulls in D via C -> {A,B,C,D}.
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 9, S1, C),
        row(W2, WeekDay.MONDAY, 9, S1, C),
        row(W2, WeekDay.MONDAY, 9, S1, D),
        # S1 slot (TUESDAY,9): disjoint pair {E,F}.
        row(W1, WeekDay.TUESDAY, 9, S1, e),
        row(W1, WeekDay.TUESDAY, 9, S1, f),
        # S2 slot (MONDAY,9): {A,G} -- A reused under a second subject.
        row(W1, WeekDay.MONDAY, 9, S2, A),
        row(W1, WeekDay.MONDAY, 9, S2, g),
        # H is heterogeneous (two slots) so it is dropped; I is left orphaned.
        row(W1, WeekDay.MONDAY, 9, S1, h),
        row(W1, WeekDay.WEDNESDAY, 9, S1, h),
        row(W1, WeekDay.WEDNESDAY, 9, S1, i),
    ]
    components = build_candidate_components(rows)

    by_blocks = _by_blocks(components)
    assert set(by_blocks) == {
        frozenset({A, B, C, D}),
        frozenset({e, f}),
        frozenset({A, g}),
    }

    s1_big = by_blocks[frozenset({A, B, C, D})]
    s1_ef = by_blocks[frozenset({e, f})]
    s2_ag = by_blocks[frozenset({A, g})]

    assert s1_big.subject_id == S1
    assert s1_ef.subject_id == S1
    assert s2_ag.subject_id == S2

    # A lives in one S1 and one S2 component with different ids and subjects.
    assert s1_big.candidate_group_id != s2_ag.candidate_group_id

    # The big S1 component: triangle edges on w1 plus the w2 connector to D.
    assert s1_big.edges == (
        CandidateEdge(A, B, (W1,)),
        CandidateEdge(A, C, (W1,)),
        CandidateEdge(B, C, (W1,)),
        CandidateEdge(C, D, (W2,)),
    )
    assert s1_ef.edges == (CandidateEdge(e, f, (W1,)),)
    assert s2_ag.edges == (CandidateEdge(A, g, (W1,)),)


# --------------------------------------------------------------------------- #
# Type / immutability guarantees
# --------------------------------------------------------------------------- #


def test_block_ids_frozenset_edges_tuple_and_dataclasses_frozen() -> None:
    """The component exposes a frozenset of blocks and a tuple of edges, and both
    dataclasses reject attribute assignment (frozen)."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert isinstance(component.block_ids, frozenset)
    assert isinstance(component.edges, tuple)
    assert all(isinstance(edge, CandidateEdge) for edge in component.edges)

    with pytest.raises(dataclasses.FrozenInstanceError):
        component.subject_id = S2  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        component.edges[0].block_a = B  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Complete graph on one slot
# --------------------------------------------------------------------------- #


def test_four_blocks_one_slot_form_k4() -> None:
    """Four blocks sharing one slot are mutually adjacent (K4): one component,
    every one of the six canonical pairs as an edge, each on that week."""
    rows = [
        row(W1, WeekDay.MONDAY, 9, S1, A),
        row(W1, WeekDay.MONDAY, 9, S1, B),
        row(W1, WeekDay.MONDAY, 9, S1, C),
        row(W1, WeekDay.MONDAY, 9, S1, D),
    ]
    components = build_candidate_components(rows)

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({A, B, C, D})

    expected_edges = tuple(
        CandidateEdge(block_a, block_b, (W1,))
        for block_a, block_b in combinations(sorted([A, B, C, D]), 2)
    )
    assert len(expected_edges) == 6  # every pair with block_a < block_b
    assert component.edges == expected_edges
    assert all(edge.block_a < edge.block_b for edge in component.edges)
    assert all(edge.weeks == (W1,) for edge in component.edges)
    assert component.candidate_group_id == _expected_group_id(S1, A, B, C, D)


# --------------------------------------------------------------------------- #
# Property-style invariants over a large, deterministically generated graph
# --------------------------------------------------------------------------- #


def _generate_rows(seed: int) -> list[CandidateSlotRow]:
    """Deterministically synthesize a large-ish slot-row set for one build.

    Uses a *seeded* ``random.Random`` (no hypothesis, no global RNG) so the
    input is fully reproducible. The shape is deliberately varied:

    * a guaranteed 3-block homogeneous cluster on an isolated slot (start_time
      20, which the random pool never uses) so at least one multi-block
      component always exists and can be named exactly;
    * a guaranteed set of heterogeneous blocks (two distinct
      ``(weekday, start_time)`` slots) that must be dropped;
    * the remaining blocks scattered over a small slot pool across several
      weeks, all anchored on ``weeks[0]`` so co-located blocks actually collide,
      which yields further multi-block components and lone (singleton) blocks.
    """
    rng = random.Random(seed)

    subjects = [uuid.UUID(int=1000 + index) for index in range(rng.randint(2, 3))]
    block_count = rng.randint(15, 30)
    blocks = [uuid.UUID(int=1 + index) for index in range(block_count)]
    weekdays = [WeekDay.MONDAY, WeekDay.TUESDAY, WeekDay.WEDNESDAY]
    start_times = [9, 11, 14]
    home_slots = [(weekday, start) for weekday in weekdays for start in start_times]
    weeks = [date(2025, 9, 1) + timedelta(days=7 * offset) for offset in range(4)]

    rows: list[CandidateSlotRow] = []

    # Isolated, guaranteed multi-block component (unique start_time 20).
    cluster = blocks[:3]
    cluster_subject = subjects[0]
    for block in cluster:
        rows.append((weeks[0], WeekDay.MONDAY, 20, cluster_subject, block))

    remaining = blocks[3:]
    het_count = max(2, len(remaining) // 5)
    het_blocks = set(rng.sample(remaining, het_count))

    for block in remaining:
        subject = rng.choice(subjects)
        weekday, start = rng.choice(home_slots)
        # Always include weeks[0] so blocks sharing subject+slot collide there.
        chosen_weeks = {weeks[0]}
        for week in weeks[1:]:
            if rng.random() < 0.5:
                chosen_weeks.add(week)
        for week in sorted(chosen_weeks):
            rows.append((week, weekday, start, subject, block))
        if block in het_blocks:
            # A second, distinct (weekday, start_time) slot -> block is dropped.
            other = rng.choice([slot for slot in home_slots if slot != (weekday, start)])
            rows.append((rng.choice(weeks), other[0], other[1], subject, block))

    rng.shuffle(rows)
    return rows


def _independent_components_by_subject(
    rows: list[CandidateSlotRow],
) -> tuple[set[uuid.UUID], dict[uuid.UUID, set[frozenset[uuid.UUID]]]]:
    """Recompute eligibility and per-subject connected components from scratch.

    Deliberately independent of the module under test: eligibility keys on the
    distinct ``(weekday, start_time)`` slots per block, and components are found
    by plain BFS over collision edges (rather than the module's union-find).
    Returns ``(dropped_blocks, {subject: {frozenset(block_ids), ...}})``.
    """
    slots_by_block: defaultdict[uuid.UUID, set[tuple[WeekDay, int]]] = defaultdict(set)
    for _week, weekday, start_time, _subject_id, block_id in rows:
        slots_by_block[block_id].add((weekday, start_time))
    eligible = {block for block, slots in slots_by_block.items() if len(slots) == 1}
    dropped = set(slots_by_block) - eligible

    blocks_by_slot: defaultdict[tuple[date, WeekDay, int, uuid.UUID], set[uuid.UUID]] = defaultdict(
        set,
    )
    for week, weekday, start_time, subject_id, block_id in rows:
        if block_id in eligible:
            blocks_by_slot[(week, weekday, start_time, subject_id)].add(block_id)

    adjacency: defaultdict[uuid.UUID, defaultdict[uuid.UUID, set[uuid.UUID]]] = defaultdict(
        lambda: defaultdict(set),
    )
    nodes_by_subject: defaultdict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for (_week, _weekday, _start_time, subject_id), blocks in blocks_by_slot.items():
        if len(blocks) < 2:
            continue
        for block_a, block_b in combinations(sorted(blocks), 2):
            adjacency[subject_id][block_a].add(block_b)
            adjacency[subject_id][block_b].add(block_a)
            nodes_by_subject[subject_id].update((block_a, block_b))

    components_by_subject: dict[uuid.UUID, set[frozenset[uuid.UUID]]] = {}
    for subject_id, nodes in nodes_by_subject.items():
        unseen = set(nodes)
        found: set[frozenset[uuid.UUID]] = set()
        while unseen:
            start = min(unseen)
            unseen.discard(start)
            component = {start}
            stack = [start]
            while stack:
                node = stack.pop()
                for neighbor in adjacency[subject_id][node]:
                    if neighbor in unseen:
                        unseen.discard(neighbor)
                        component.add(neighbor)
                        stack.append(neighbor)
            found.add(frozenset(component))
        components_by_subject[subject_id] = found

    return dropped, components_by_subject


@pytest.mark.parametrize("seed", [1, 7, 1234])
def test_build_invariants_on_large_generated_graph(seed: int) -> None:
    """Structural invariants must hold on a large, reproducible random build."""
    rows = _generate_rows(seed)
    components = build_candidate_components(rows)

    dropped, expected_by_subject = _independent_components_by_subject(rows)

    # The generator guarantees both code paths are exercised.
    assert dropped, "expected at least one dropped heterogeneous block"
    assert components, "expected at least one component"

    for component in components:
        # No singleton or empty components ever surface.
        assert len(component.block_ids) >= 2
        # Edges are canonical and internal to the component.
        for edge in component.edges:
            assert edge.block_a < edge.block_b
            assert edge.block_a in component.block_ids
            assert edge.block_b in component.block_ids
        # The id is the golden uuid5 of subject + sorted membership.
        assert component.candidate_group_id == _expected_group_id(
            component.subject_id,
            *component.block_ids,
        )
        # No dropped (heterogeneous) block ever appears in a component.
        assert component.block_ids.isdisjoint(dropped)

    got_by_subject: defaultdict[uuid.UUID, list[frozenset[uuid.UUID]]] = defaultdict(list)
    for component in components:
        got_by_subject[component.subject_id].append(component.block_ids)

    # The subjects with components match the independent recomputation.
    assert set(got_by_subject) == set(expected_by_subject)

    for subject_id, block_id_sets in got_by_subject.items():
        # Within a subject the components partition their blocks (disjoint).
        seen: set[uuid.UUID] = set()
        for block_ids in block_id_sets:
            assert seen.isdisjoint(block_ids)
            seen |= block_ids
        # And the exact set of components matches the independent BFS result.
        assert set(block_id_sets) == expected_by_subject[subject_id]

    # The guaranteed isolated cluster surfaces exactly as its own component.
    cluster = frozenset(uuid.UUID(int=1 + index) for index in range(3))
    assert cluster in set(got_by_subject[uuid.UUID(int=1000)])
