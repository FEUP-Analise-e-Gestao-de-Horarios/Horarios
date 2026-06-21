import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from uuid import NAMESPACE_OID, UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.queries.parallel_block_candidates import (
    block_details_stmt,
    block_weeks_stmt,
    candidate_slot_members_stmt,
)
from src.projects.projects_db.models.parallel_block_group_member import ParallelBlockGroupMember
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateClass,
    ParallelBlockCandidateDegree,
    ParallelBlockCandidateGroupResponse,
    ParallelBlockCandidateNode,
    ParallelBlockCandidateSession,
    ParallelBlockCandidateSubject,
    ParallelBlockCandidateYear,
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
class _YearDegree:
    """A ``years`` row (one per degree) the subject is taught in."""

    year_id: UUID
    year_number: int
    degree_id: UUID
    degree_acronym: str
    degree_name: str


@dataclass(frozen=True)
class _BlockDetail:
    classes: list[ParallelBlockCandidateClass]
    session_type: str
    start_time: int
    duration: int
    weekday: WeekDay
    subject_id: UUID
    subject_acronym: str
    subject_name: str
    year_degrees: tuple[_YearDegree, ...]


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
        rows = self.session.execute(candidate_slot_members_stmt()).all()

        # Blocks sharing a (week, weekday, start_time, subject) slot are mutually
        # adjacent. Grouping per slot avoids a quadratic sessions self-join.
        blocks_by_slot: defaultdict[tuple, set[UUID]] = defaultdict(set)
        for week, weekday, start_time, subject_id, block_id in rows:
            blocks_by_slot[(week, weekday, start_time, subject_id)].add(block_id)

        union_find = _UnionFind()
        edges: set[tuple[UUID, UUID]] = set()
        for blocks in blocks_by_slot.values():
            if len(blocks) < 2:
                continue
            for block_a, block_b in combinations(sorted(blocks), 2):
                edges.add((block_a, block_b))
                union_find.union(block_a, block_b)

        blocks_by_root: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for block_id in list(union_find.parent):
            blocks_by_root[union_find.find(block_id)].add(block_id)

        edges_by_root: defaultdict[UUID, list[tuple[UUID, UUID]]] = defaultdict(list)
        for block_a, block_b in edges:
            edges_by_root[union_find.find(block_a)].append((block_a, block_b))

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
                        confirmed_group_id=confirmed.get(block_id),
                        classes=detail.classes,
                        session=ParallelBlockCandidateSession(
                            type=detail.session_type,
                            start_time=detail.start_time,
                            duration=detail.duration,
                        ),
                        first_week=first_week,
                        last_week=last_week,
                        year_ids=[
                            year_degree.year_id
                            for year_degree in sorted(
                                detail.year_degrees,
                                key=lambda yd: (yd.year_number, yd.degree_acronym),
                            )
                        ],
                    ),
                )

            if len(nodes) < 2:
                continue

            representative = details[nodes[0].original_block_id]

            # Collect the year/degree rows present across the whole group, keyed
            # by year id (each year row belongs to a single degree).
            years_by_id: dict[UUID, _YearDegree] = {}
            for node in nodes:
                for year_degree in details[node.original_block_id].year_degrees:
                    years_by_id.setdefault(year_degree.year_id, year_degree)

            subject = ParallelBlockCandidateSubject(
                id=representative.subject_id,
                acronym=representative.subject_acronym,
                name=representative.subject_name,
                years=[
                    ParallelBlockCandidateYear(
                        id=year_degree.year_id,
                        degree=ParallelBlockCandidateDegree(
                            id=year_degree.degree_id,
                            acronym=year_degree.degree_acronym,
                            name=year_degree.degree_name,
                        ),
                    )
                    for year_degree in sorted(
                        years_by_id.values(),
                        key=lambda yd: (yd.year_number, yd.degree_acronym),
                    )
                ],
            )

            edges = [(a, b) for a, b in component.edges if a in details and b in details]
            groups.append(
                ParallelBlockCandidateGroupResponse(
                    candidate_group_id=component.candidate_group_id,
                    subject=subject,
                    weekday=representative.weekday,
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

        classes: defaultdict[UUID, dict[UUID, str]] = defaultdict(dict)
        year_degrees: defaultdict[UUID, dict[UUID, _YearDegree]] = defaultdict(dict)
        representative = {}
        for row in rows:
            classes[row.original_block_id].setdefault(row.class_id, row.class_code)
            year_degrees[row.original_block_id].setdefault(
                row.year_id,
                _YearDegree(
                    year_id=row.year_id,
                    year_number=row.year,
                    degree_id=row.degree_id,
                    degree_acronym=row.degree_acronym,
                    degree_name=row.degree_name,
                ),
            )
            representative.setdefault(row.original_block_id, row)

        return {
            block_id: _BlockDetail(
                classes=[
                    ParallelBlockCandidateClass(id=class_id, code=code)
                    for class_id, code in sorted(
                        classes[block_id].items(),
                        key=lambda item: item[1],
                    )
                ],
                session_type=row.session_type,
                start_time=row.start_time,
                duration=row.duration,
                weekday=row.weekday,
                subject_id=row.subject_id,
                subject_acronym=row.subject_acronym,
                subject_name=row.subject_name,
                year_degrees=tuple(year_degrees[block_id].values()),
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
