"""Pure graph logic for parallel block candidate detection.

Blocks that collide on at least one week at the same weekday and start time
for a shared subject form an overlap graph; candidate groups are its connected
components, built independently per subject so a component only ever holds
blocks and edges of a single subject. A block taught under several subjects
can therefore appear in one component per subject. Nothing here touches the
database — the DAO feeds this module the slot rows and consumes the resulting
components.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from uuid import NAMESPACE_OID, UUID

from src.projects.projects_db.schemas.weekday import WeekDay

CandidateSlotRow = tuple[date, WeekDay, int, UUID, UUID]
"""A ``(week, weekday, start_time, subject_id, original_block_id)`` row."""


def _component_uuid(subject_id: UUID, block_ids: Iterable[UUID]) -> UUID:
    """Deterministic id for a component, from its subject and sorted member blocks.

    Because the id changes whenever the component's membership changes, a stale
    ``candidate_group_id`` submitted on save no longer matches any component and
    is rejected. The subject prefix keeps two subjects' components distinct
    even when their block membership is identical.
    """
    members = ",".join(str(block_id) for block_id in sorted(block_ids))
    return uuid.uuid5(NAMESPACE_OID, f"{subject_id}:{members}")


@dataclass(frozen=True)
class CandidateEdge:
    """An undirected adjacency between two blocks, with the weeks they collide on.

    ``block_a`` and ``block_b`` are sorted so each unordered pair has one
    canonical edge; ``weeks`` are the (sorted) weeks both blocks share a slot.
    """

    block_a: UUID
    block_b: UUID
    weeks: tuple[date, ...]


@dataclass(frozen=True)
class CandidateComponent:
    """A connected component of one subject's parallel-candidate overlap graph."""

    candidate_group_id: UUID
    subject_id: UUID
    block_ids: frozenset[UUID]
    edges: tuple[CandidateEdge, ...]

    def is_connected_subset(self, blocks: set[UUID]) -> bool:
        """Whether ``blocks`` is a connected subgraph of this component.

        A valid saved group is a connected selection: every block must be
        reachable from any other through edges whose both endpoints are also
        selected.
        """
        if len(blocks) < 2 or not blocks <= self.block_ids:
            return False

        adjacency: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for edge in self.edges:
            if edge.block_a in blocks and edge.block_b in blocks:
                adjacency[edge.block_a].add(edge.block_b)
                adjacency[edge.block_b].add(edge.block_a)

        start = next(iter(blocks))
        seen = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        return seen == blocks


class _UnionFind:
    """Disjoint-set forest with path compression, keyed by block id."""

    def __init__(self) -> None:
        self.parent: dict[UUID, UUID] = {}

    def find(self, block_id: UUID) -> UUID:
        self.parent.setdefault(block_id, block_id)
        root = block_id
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[block_id] != root:
            self.parent[block_id], block_id = root, self.parent[block_id]
        return root

    def union(self, block_a: UUID, block_b: UUID) -> None:
        root_a, root_b = self.find(block_a), self.find(block_b)
        if root_a != root_b:
            self.parent[root_a] = root_b


def build_candidate_components(rows: Iterable[CandidateSlotRow]) -> list[CandidateComponent]:
    """Build the candidate groups as connected components with their edges."""
    rows = list(rows)

    # A block only qualifies if every session under it happens at the same
    # weekday and start time. An edit that moves a single week to a different
    # weekday or start_time leaves the block_id spanning a heterogeneous set
    # of sessions; rather than represent it by an arbitrary slot, drop it from
    # candidate detection entirely.
    slots_by_block: defaultdict[UUID, set[tuple[WeekDay, int]]] = defaultdict(set)
    for _week, weekday, start_time, _subject_id, block_id in rows:
        slots_by_block[block_id].add((weekday, start_time))
    eligible_blocks = {block_id for block_id, slots in slots_by_block.items() if len(slots) == 1}

    # Blocks sharing a (week, weekday, start_time, subject) slot are mutually
    # adjacent. Grouping per slot avoids a quadratic sessions self-join.
    blocks_by_slot: defaultdict[tuple[date, WeekDay, int, UUID], set[UUID]] = defaultdict(set)
    for week, weekday, start_time, subject_id, block_id in rows:
        if block_id not in eligible_blocks:
            continue
        blocks_by_slot[(week, weekday, start_time, subject_id)].add(block_id)

    # Each subject gets its own graph: a block taught under two subjects must
    # not bridge them into one component, and edges carry only the weeks the
    # blocks collide on for that subject.
    union_finds: defaultdict[UUID, _UnionFind] = defaultdict(_UnionFind)
    weeks_by_edge: defaultdict[UUID, defaultdict[tuple[UUID, UUID], set[date]]] = defaultdict(
        lambda: defaultdict(set),
    )
    for (week, _weekday, _start_time, subject_id), blocks in blocks_by_slot.items():
        if len(blocks) < 2:
            continue
        union_find = union_finds[subject_id]
        for block_a, block_b in combinations(sorted(blocks), 2):
            weeks_by_edge[subject_id][(block_a, block_b)].add(week)
            union_find.union(block_a, block_b)

    components: list[CandidateComponent] = []
    for subject_id, union_find in union_finds.items():
        blocks_by_root: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for block_id in list(union_find.parent):
            blocks_by_root[union_find.find(block_id)].add(block_id)

        edges_by_root: defaultdict[UUID, list[CandidateEdge]] = defaultdict(list)
        for (block_a, block_b), weeks in weeks_by_edge[subject_id].items():
            edge = CandidateEdge(block_a, block_b, tuple(sorted(weeks)))
            edges_by_root[union_find.find(block_a)].append(edge)

        components.extend(
            CandidateComponent(
                candidate_group_id=_component_uuid(subject_id, block_ids),
                subject_id=subject_id,
                block_ids=frozenset(block_ids),
                edges=tuple(sorted(edges_by_root[root], key=lambda e: (e.block_a, e.block_b))),
            )
            for root, block_ids in blocks_by_root.items()
        )
    return components
