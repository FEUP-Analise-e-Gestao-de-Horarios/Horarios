"""White-box unit tests for the pure graph helpers behind parallel candidates.

These exercise ``parallel_candidate_graph`` in isolation: no database, no
Django. Underscore-prefixed names are imported and constructed directly on
purpose — this file pins the internal contracts (deterministic component ids,
connected-subset detection, union-find with path compression, and the frozen
dataclasses) that ``build_candidate_components`` relies on. Behaviors that only
emerge through ``build_candidate_components`` (determinism/membership through a
full build) are covered elsewhere; here everything is constructed by hand.
"""

import dataclasses
import uuid
from datetime import date
from uuid import NAMESPACE_OID

import pytest

from src.projects.projects_db.dao.parallel_candidate_graph import (
    CandidateComponent,
    CandidateEdge,
    _component_uuid,
    _UnionFind,
)

# Fixed block ids: readable, ordered (A < B < C < D < E by uuid.int).
A = uuid.UUID(int=1)
B = uuid.UUID(int=2)
C = uuid.UUID(int=3)
D = uuid.UUID(int=4)
E = uuid.UUID(int=5)

# Two distinct subjects.
S1 = uuid.UUID(int=100)
S2 = uuid.UUID(int=101)

# A couple of week dates for CandidateEdge.weeks.
W1 = date(2025, 9, 15)
W2 = date(2025, 9, 22)


def _component(
    block_ids: set[uuid.UUID],
    edges: tuple[CandidateEdge, ...],
    *,
    subject_id: uuid.UUID = S1,
) -> CandidateComponent:
    """Build a component directly, deriving its id from its membership."""
    return CandidateComponent(
        candidate_group_id=_component_uuid(subject_id, block_ids),
        subject_id=subject_id,
        block_ids=frozenset(block_ids),
        edges=edges,
    )


# --------------------------------------------------------------------------- #
# _component_uuid
# --------------------------------------------------------------------------- #


def test_component_uuid_deterministic_and_golden() -> None:
    """Equals the golden uuid5 of ``{subject}:{sorted members}`` and is a v5 uuid."""
    first = _component_uuid(S1, [A, B])
    second = _component_uuid(S1, [A, B])
    golden = uuid.uuid5(NAMESPACE_OID, f"{S1}:{A},{B}")

    assert first == second
    assert first == golden
    assert first.version == 5


@pytest.mark.parametrize(
    "members",
    [
        [A, B],
        [B, A],
        {A, B},
        frozenset({A, B}),
        (A, B),
        (block for block in (B, A)),
    ],
)
def test_component_uuid_invariant_to_ordering_and_iterable(members: object) -> None:
    """Order and iterable type of the members do not change the id."""
    assert _component_uuid(S1, members) == _component_uuid(S1, [A, B])  # type: ignore[arg-type]


def test_component_uuid_changes_on_membership_add() -> None:
    """Adding a block yields a different id."""
    assert _component_uuid(S1, [A, B]) != _component_uuid(S1, [A, B, C])


def test_component_uuid_changes_on_membership_remove() -> None:
    """Removing/swapping a block yields a different id."""
    assert _component_uuid(S1, [A, B, C]) != _component_uuid(S1, [A, C])


def test_component_uuid_subject_prefix_disambiguates() -> None:
    """Identical membership under different subjects produces different ids."""
    assert _component_uuid(S1, [A, B]) != _component_uuid(S2, [A, B])


def test_component_uuid_single_member_stable_and_distinct() -> None:
    """A single-member id is stable and differs from the two-member id."""
    assert _component_uuid(S1, [A]) == _component_uuid(S1, [A])
    assert _component_uuid(S1, [A]) != _component_uuid(S1, [A, B])


def test_component_uuid_empty_member_deterministic() -> None:
    """An empty membership is deterministic and does not raise."""
    assert _component_uuid(S1, []) == _component_uuid(S1, [])
    assert _component_uuid(S1, []) == uuid.uuid5(NAMESPACE_OID, f"{S1}:")


# --------------------------------------------------------------------------- #
# CandidateComponent.is_connected_subset
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("selection", [set(), {A}, {B}, {C}])
def test_is_connected_subset_false_for_fewer_than_two(selection: set[uuid.UUID]) -> None:
    """A selection of zero or one block is never a connected subset."""
    component = _component(
        {A, B, C},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(B, C, (W1,))),
    )
    assert component.is_connected_subset(selection) is False


@pytest.mark.parametrize("selection", [{A, B, D}, {D, E}])
def test_is_connected_subset_false_when_not_a_subset(selection: set[uuid.UUID]) -> None:
    """A selection containing non-members short-circuits to False."""
    component = _component(
        {A, B, C},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(B, C, (W1,))),
    )
    assert component.is_connected_subset(selection) is False


@pytest.mark.parametrize("selection", [{A, B, C}, {A, B}, {B, C}])
def test_is_connected_subset_true_for_full_and_connected_two(
    selection: set[uuid.UUID],
) -> None:
    """The whole chain and any adjacent 2-subset are connected."""
    component = _component(
        {A, B, C},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(B, C, (W1,))),
    )
    assert component.is_connected_subset(selection) is True


def test_is_connected_subset_false_through_unselected_hinge() -> None:
    """A and C are only linked via B; without B the selection is disconnected."""
    component = _component(
        {A, B, C},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(B, C, (W1,))),
    )
    assert component.is_connected_subset({A, C}) is False


def test_is_connected_subset_false_when_edges_missing() -> None:
    """A single edge cannot span three selected blocks."""
    component = _component({A, B, C}, (CandidateEdge(A, B, (W1,)),))
    assert component.is_connected_subset({A, B, C}) is False


def test_is_connected_subset_false_for_two_disjoint_pairs() -> None:
    """Two disjoint edges over four blocks never form one connected selection."""
    component = _component(
        {A, B, C, D},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(C, D, (W1,))),
    )
    assert component.is_connected_subset({A, B, C, D}) is False


def test_is_connected_subset_ignores_partially_selected_edges() -> None:
    """Edges touching an unselected endpoint are dropped, isolating D."""
    component = _component(
        {A, B, C, D},
        (
            CandidateEdge(A, B, (W1,)),
            CandidateEdge(B, C, (W1,)),
            CandidateEdge(C, D, (W1,)),
        ),
    )
    # Selecting {A, B, D}: only A-B survives (B-C and C-D touch unselected C),
    # so D is isolated.
    assert component.is_connected_subset({A, B, D}) is False


@pytest.mark.parametrize("selection", [{A, B, C, D}, {B, C, D}])
def test_is_connected_subset_true_over_longer_chain(
    selection: set[uuid.UUID],
) -> None:
    """A full path and a connected tail of it are both connected."""
    component = _component(
        {A, B, C, D},
        (
            CandidateEdge(A, B, (W1,)),
            CandidateEdge(B, C, (W1,)),
            CandidateEdge(C, D, (W1,)),
        ),
    )
    assert component.is_connected_subset(selection) is True


@pytest.mark.parametrize("selection", [{A, B}, {A, C}, {B, C}, {A, B, C}])
def test_is_connected_subset_true_over_triangle(selection: set[uuid.UUID]) -> None:
    """Any subset of a triangle of size >= 2 is connected."""
    component = _component(
        {A, B, C},
        (
            CandidateEdge(A, B, (W1,)),
            CandidateEdge(A, C, (W1,)),
            CandidateEdge(B, C, (W1,)),
        ),
    )
    assert component.is_connected_subset(selection) is True


def test_is_connected_subset_robust_to_duplicate_edges() -> None:
    """Parallel edges between the same pair do not break traversal."""
    component = _component(
        {A, B},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(A, B, (W2,))),
    )
    assert component.is_connected_subset({A, B}) is True


def test_is_connected_subset_does_not_mutate_inputs() -> None:
    """Neither the passed selection set nor the component is mutated."""
    component = _component(
        {A, B, C},
        (CandidateEdge(A, B, (W1,)), CandidateEdge(B, C, (W1,))),
    )
    selection = {A, B, C}
    selection_snapshot = set(selection)
    block_ids_snapshot = frozenset(component.block_ids)
    edges_snapshot = component.edges

    component.is_connected_subset(selection)

    assert selection == selection_snapshot
    assert component.block_ids == block_ids_snapshot
    assert component.edges == edges_snapshot


# --------------------------------------------------------------------------- #
# _UnionFind
# --------------------------------------------------------------------------- #


def test_union_find_find_fresh_element_self_initializes() -> None:
    """find on an unseen element registers it as its own root, idempotently."""
    uf = _UnionFind()
    assert uf.find(A) == A
    assert uf.find(A) == A
    assert uf.parent == {A: A}


@pytest.mark.parametrize(
    ("first", "second", "expected_root"),
    [(A, B, B), (B, A, A)],
)
def test_union_find_second_arg_root_wins(
    first: uuid.UUID,
    second: uuid.UUID,
    expected_root: uuid.UUID,
) -> None:
    """union attaches the first arg's root under the second arg's root."""
    uf = _UnionFind()
    uf.union(first, second)
    assert uf.find(first) == expected_root
    assert uf.find(second) == expected_root
    assert uf.parent[first] == expected_root


def test_union_find_chained_unions_single_component() -> None:
    """A chain of unions collapses every element into one component."""
    uf = _UnionFind()
    uf.union(A, B)
    uf.union(B, C)
    uf.union(C, D)
    assert len({uf.find(A), uf.find(B), uf.find(C), uf.find(D)}) == 1


def test_union_find_redundant_and_self_union_are_noops() -> None:
    """Re-unioning joined elements or self-unioning changes nothing."""
    uf = _UnionFind()
    uf.union(A, B)
    root_before = uf.find(A)

    uf.union(A, B)
    uf.union(B, A)
    uf.union(A, A)

    assert uf.find(A) == root_before
    assert uf.find(B) == root_before
    assert uf.find(A) == uf.find(B)


def test_union_find_merges_two_separate_sets() -> None:
    """Two independently-built sets become one after a bridging union."""
    uf = _UnionFind()
    uf.union(A, B)
    uf.union(C, D)
    assert len({uf.find(A), uf.find(B), uf.find(C), uf.find(D)}) == 2

    uf.union(B, C)
    assert len({uf.find(A), uf.find(B), uf.find(C), uf.find(D)}) == 1


def test_union_find_find_path_compression_flattens_branch() -> None:
    """find rewires every node on the queried branch straight to the root."""
    uf = _UnionFind()
    uf.parent = {A: B, B: C, C: D, D: D}

    assert uf.find(A) == D
    assert uf.parent[A] == D
    assert uf.parent[B] == D
    assert uf.parent[C] == D


def test_union_find_find_compresses_only_queried_branch() -> None:
    """A node off the queried branch is untouched until it is itself queried."""
    uf = _UnionFind()
    uf.parent = {A: B, B: D, D: D, E: B}

    assert uf.find(A) == D
    # A and B were on the queried branch; E was not.
    assert uf.parent[A] == D
    assert uf.parent[B] == D
    assert uf.parent[E] == B

    # Querying E now compresses it too.
    assert uf.find(E) == D
    assert uf.parent[E] == D


def test_union_find_find_on_root_is_noop() -> None:
    """find on a root returns it and leaves the forest unchanged."""
    uf = _UnionFind()
    uf.union(A, B)  # B is the root
    assert uf.find(B) == B
    assert uf.parent[B] == B


def test_union_find_find_stable_after_compression() -> None:
    """Repeated find on a compressed branch keeps returning the same root."""
    uf = _UnionFind()
    uf.parent = {A: B, B: C, C: C}

    assert uf.find(A) == C
    assert uf.parent[A] == C
    assert uf.parent[B] == C
    # Idempotent on repeat, and the root is a no-op.
    assert uf.find(A) == C
    assert uf.find(B) == C
    assert uf.parent[A] == C
    assert uf.parent[B] == C


# --------------------------------------------------------------------------- #
# CandidateEdge / CandidateComponent dataclass contracts
# --------------------------------------------------------------------------- #


def test_candidate_edge_value_equality_hash_and_frozen() -> None:
    """Identical edges compare equal, hash equal, key a dict, and are frozen."""
    edge_one = CandidateEdge(A, B, (W1, W2))
    edge_two = CandidateEdge(A, B, (W1, W2))

    assert edge_one == edge_two
    assert hash(edge_one) == hash(edge_two)
    assert {edge_one: "x"}[edge_two] == "x"

    with pytest.raises(dataclasses.FrozenInstanceError):
        edge_one.block_a = C  # type: ignore[misc]


def test_candidate_component_value_equality_hash_and_frozen() -> None:
    """Identical components compare equal, hash equal, key a dict, and are frozen."""
    edges = (CandidateEdge(A, B, (W1,)),)
    component_one = CandidateComponent(
        candidate_group_id=_component_uuid(S1, {A, B}),
        subject_id=S1,
        block_ids=frozenset({A, B}),
        edges=edges,
    )
    component_two = CandidateComponent(
        candidate_group_id=_component_uuid(S1, {A, B}),
        subject_id=S1,
        block_ids=frozenset({A, B}),
        edges=edges,
    )

    assert component_one == component_two
    assert hash(component_one) == hash(component_two)
    assert {component_one: "y"}[component_two] == "y"

    with pytest.raises(dataclasses.FrozenInstanceError):
        component_one.subject_id = S2  # type: ignore[misc]
