import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import NAMESPACE_OID, UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.queries.parallel_block_candidates import (
    block_details_stmt,
    block_weeks_stmt,
    candidate_edges_stmt,
)
from src.projects.projects_db.models.parallel_block_group_member import ParallelBlockGroupMember
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateGroupResponse,
    ParallelBlockCandidateNode,
)
from src.projects.projects_db.schemas.weekday import WeekDay


def _component_uuid(block_ids: Iterable[UUID]) -> UUID:
    """Deterministic id for a component, derived from its sorted member blocks.

    Because the id changes whenever the component's membership changes, a stale
    ``candidate_group_id`` submitted on save no longer matches any component and
    is rejected.
    """
    return uuid.uuid5(NAMESPACE_OID, ",".join(str(block_id) for block_id in sorted(block_ids)))


@dataclass(frozen=True)
class _BlockDetail:
    class_codes: list[str]
    session_type: str
    duration: int
    weekday: WeekDay
    start_time: int
    subject_name: str
    year: int
    degree_id: UUID
    degree_name: str
    degree_acronym: str


@dataclass(frozen=True)
class CandidateComponent:
    """A connected component of the parallel-candidate overlap graph."""

    candidate_group_id: UUID
    block_ids: frozenset[UUID]
    edges: tuple[tuple[UUID, UUID], ...]

    def is_connected_subset(self, blocks: set[UUID]) -> bool:
        """Whether ``blocks`` is a connected subgraph of this component.

        A valid saved group is a connected selection: every block must be
        reachable from any other through edges whose both endpoints are also
        selected.
        """
        if len(blocks) < 2 or not blocks <= self.block_ids:
            return False

        adjacency: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for block_a, block_b in self.edges:
            if block_a in blocks and block_b in blocks:
                adjacency[block_a].add(block_b)
                adjacency[block_b].add(block_a)

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


class ParallelBlockCandidateDAO:
    """Data access object for detected parallel block candidates.

    Candidates are computed on every request as the connected components of an
    overlap graph: blocks of the same subject that collide on at least one week
    at the same weekday and start time. Nothing is persisted here; only
    confirmed groups (``ParallelBlockGroupMember``) are stored.

    Not a ``BaseDAO`` subclass: there is no persistent model to operate on.
    """

    def __init__(self, session: DBSession) -> None:
        self.session = session

    # -------------------------------------------------------------------
    # -- Components (graph topology only)
    # -------------------------------------------------------------------

    def get_candidate_components(self) -> list[CandidateComponent]:
        """Return the candidate groups as connected components with their edges."""
        edge_rows = self.session.execute(candidate_edges_stmt()).all()

        union_find = _UnionFind()
        for row in edge_rows:
            union_find.union(row.block_a, row.block_b)

        blocks_by_root: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for block_id in list(union_find.parent):
            blocks_by_root[union_find.find(block_id)].add(block_id)

        edges_by_root: defaultdict[UUID, list[tuple[UUID, UUID]]] = defaultdict(list)
        for row in edge_rows:
            edges_by_root[union_find.find(row.block_a)].append((row.block_a, row.block_b))

        return [
            CandidateComponent(
                candidate_group_id=_component_uuid(block_ids),
                block_ids=frozenset(block_ids),
                edges=tuple(sorted(edges_by_root[root])),
            )
            for root, block_ids in blocks_by_root.items()
        ]

    # -------------------------------------------------------------------
    # -- Components with display info
    # -------------------------------------------------------------------

    def get_all_groups_with_info(self) -> list[ParallelBlockCandidateGroupResponse]:
        """Return all candidate groups with per-block session and degree info."""
        components = self.get_candidate_components()
        if not components:
            return []

        all_block_ids = [block_id for component in components for block_id in component.block_ids]
        details = self._block_details(all_block_ids)
        weeks = self._block_weeks(all_block_ids)
        confirmed = self._confirmed_group_by_block(all_block_ids)

        groups: list[ParallelBlockCandidateGroupResponse] = []
        for component in components:
            nodes: list[ParallelBlockCandidateNode] = []
            for block_id in sorted(component.block_ids):
                detail = details.get(block_id)
                if detail is None or block_id not in weeks:
                    continue
                first_week, last_week = weeks[block_id]
                nodes.append(
                    ParallelBlockCandidateNode(
                        original_block_id=block_id,
                        class_codes=detail.class_codes,
                        session_type=detail.session_type,
                        session_duration=detail.duration,
                        first_week=first_week,
                        last_week=last_week,
                        year=detail.year,
                        degree_id=detail.degree_id,
                        degree_name=detail.degree_name,
                        degree_acronym=detail.degree_acronym,
                        confirmed_group_id=confirmed.get(block_id),
                    ),
                )

            if len(nodes) < 2:
                continue

            representative = details[nodes[0].original_block_id]
            edges = [(a, b) for a, b in component.edges if a in details and b in details]
            groups.append(
                ParallelBlockCandidateGroupResponse(
                    candidate_group_id=component.candidate_group_id,
                    subject_name=representative.subject_name,
                    session_weekday=representative.weekday,
                    session_start_time=representative.start_time,
                    nodes=nodes,
                    edges=edges,
                ),
            )

        return groups

    # -------------------------------------------------------------------
    # -- Helpers
    # -------------------------------------------------------------------

    def _block_details(self, block_ids: Sequence[UUID]) -> dict[UUID, _BlockDetail]:
        rows = self.session.execute(block_details_stmt(block_ids)).all()

        class_codes: defaultdict[UUID, set[str]] = defaultdict(set)
        representative = {}
        for row in rows:
            class_codes[row.original_block_id].add(row.class_code)
            representative.setdefault(row.original_block_id, row)

        return {
            block_id: _BlockDetail(
                class_codes=sorted(class_codes[block_id]),
                session_type=row.session_type,
                duration=row.duration,
                weekday=row.weekday,
                start_time=row.start_time,
                subject_name=row.subject_name,
                year=row.year,
                degree_id=row.degree_id,
                degree_name=row.degree_name,
                degree_acronym=row.degree_acronym,
            )
            for block_id, row in representative.items()
        }

    def _block_weeks(self, block_ids: Sequence[UUID]) -> dict[UUID, tuple[date, date]]:
        rows = self.session.execute(block_weeks_stmt(block_ids)).all()
        return {row.original_block_id: (row.first_week, row.last_week) for row in rows}

    def _confirmed_group_by_block(self, block_ids: Sequence[UUID]) -> dict[UUID, UUID]:
        rows = self.session.execute(
            select(
                ParallelBlockGroupMember.original_block_id,
                ParallelBlockGroupMember.parallel_block_group_id,
            ).where(ParallelBlockGroupMember.original_block_id.in_(block_ids)),
        ).all()
        return {row.original_block_id: row.parallel_block_group_id for row in rows}
