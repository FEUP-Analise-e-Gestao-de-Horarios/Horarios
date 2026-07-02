from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.parallel_candidate_graph import (
    CandidateComponent,
    build_candidate_components,
)
from src.projects.projects_db.dao.queries.parallel_block_candidates import (
    block_details_stmt,
    block_weeks_stmt,
    candidate_slot_members_stmt,
)
from src.projects.projects_db.models.parallel_block_group_member import ParallelBlockGroupMember
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateClass,
    ParallelBlockCandidateDegree,
    ParallelBlockCandidateEdge,
    ParallelBlockCandidateGroup,
    ParallelBlockCandidateNode,
    ParallelBlockCandidateSession,
    ParallelBlockCandidateSubject,
    ParallelBlockCandidateYear,
)
from src.projects.projects_db.schemas.weekday import WeekDay


@dataclass(frozen=True)
class _YearDegree:
    """A ``years`` row (one per degree) the subject is taught in."""

    year_id: UUID
    year_number: int
    degree_id: UUID
    degree_acronym: str
    degree_name: str


@dataclass(frozen=True)
class _SubjectInfo:
    acronym: str
    name: str


@dataclass(frozen=True)
class _BlockDetail:
    classes: list[ParallelBlockCandidateClass]
    session_type: str
    start_time: int
    duration: int
    weekday: WeekDay
    year_degrees_by_subject: dict[UUID, tuple[_YearDegree, ...]]


class ParallelBlockCandidateDAO:
    """Data access object for detected parallel block candidates.

    Candidates are computed on every request as the connected components of a
    per-subject overlap graph: blocks that collide on at least one week at the
    same weekday and start time for a shared subject. Nothing is persisted
    here; only confirmed groups (``ParallelBlockGroupMember``) are stored.

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
        return build_candidate_components(rows)

    # -------------------------------------------------------------------
    # -- Components with display info
    # -------------------------------------------------------------------

    def get_all_groups_with_info(self) -> list[ParallelBlockCandidateGroup]:
        """Return all candidate groups with per-block session and degree info."""
        components = self.get_candidate_components()
        if not components:
            return []

        all_block_ids = list(
            {block_id for component in components for block_id in component.block_ids},
        )
        details, subjects = self._block_details(all_block_ids)
        weeks = self._block_weeks(all_block_ids)
        confirmed = self._confirmed_group_by_block(all_block_ids)

        groups: list[ParallelBlockCandidateGroup] = []
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
                    ),
                )

            if len(nodes) < 2:
                continue

            representative = details[nodes[0].original_block_id]

            # Collect the year/degree rows present across the whole group for
            # the component's subject, keyed by year id (each year row belongs
            # to a single degree).
            years_by_id: dict[UUID, _YearDegree] = {}
            for node in nodes:
                block_year_degrees = details[node.original_block_id].year_degrees_by_subject
                for year_degree in block_year_degrees.get(component.subject_id, ()):
                    years_by_id.setdefault(year_degree.year_id, year_degree)

            subject_info = subjects[component.subject_id]
            subject = ParallelBlockCandidateSubject(
                id=component.subject_id,
                acronym=subject_info.acronym,
                name=subject_info.name,
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

            edges = [
                ParallelBlockCandidateEdge(
                    source=edge.block_a,
                    target=edge.block_b,
                    weeks=list(edge.weeks),
                )
                for edge in component.edges
                if edge.block_a in details and edge.block_b in details
            ]
            groups.append(
                ParallelBlockCandidateGroup(
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

    def _block_details(
        self,
        block_ids: Sequence[UUID],
    ) -> tuple[dict[UUID, _BlockDetail], dict[UUID, _SubjectInfo]]:
        rows = self.session.execute(block_details_stmt(block_ids)).all()

        classes: defaultdict[UUID, dict[UUID, tuple[str, UUID]]] = defaultdict(dict)
        year_degrees: defaultdict[UUID, defaultdict[UUID, dict[UUID, _YearDegree]]] = defaultdict(
            lambda: defaultdict(dict),
        )
        subjects: dict[UUID, _SubjectInfo] = {}
        representative = {}
        for row in rows:
            classes[row.original_block_id].setdefault(
                row.class_id,
                (row.class_code, row.year_id),
            )
            year_degrees[row.original_block_id][row.subject_id].setdefault(
                row.year_id,
                _YearDegree(
                    year_id=row.year_id,
                    year_number=row.year,
                    degree_id=row.degree_id,
                    degree_acronym=row.degree_acronym,
                    degree_name=row.degree_name,
                ),
            )
            subjects.setdefault(
                row.subject_id,
                _SubjectInfo(acronym=row.subject_acronym, name=row.subject_name),
            )
            representative.setdefault(row.original_block_id, row)

        details = {
            block_id: _BlockDetail(
                classes=[
                    ParallelBlockCandidateClass(id=class_id, code=code, year_id=year_id)
                    for class_id, (code, year_id) in sorted(
                        classes[block_id].items(),
                        key=lambda item: item[1][0],
                    )
                ],
                session_type=row.session_type,
                start_time=row.start_time,
                duration=row.duration,
                weekday=row.weekday,
                year_degrees_by_subject={
                    subject_id: tuple(by_year.values())
                    for subject_id, by_year in year_degrees[block_id].items()
                },
            )
            for block_id, row in representative.items()
        }
        return details, subjects

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
