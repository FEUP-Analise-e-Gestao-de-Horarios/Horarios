import uuid
from collections import defaultdict
from uuid import NAMESPACE_OID, UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.queries.parallel_block_candidates import candidate_blocks_cte
from src.projects.projects_db.models import (
    Class,
    Degree,
    Session,
    SessionClassSubject,
    Subject,
    Year,
)
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateDetailResponse,
    ParallelBlockCandidateFilters,
    ParallelBlockCandidateSession,
)


def _group_uuid(
    first_week: object,
    weekday: object,
    start_time: object,
    subject_id: object,
) -> UUID:
    """Deterministic UUID for a candidate group derived from its discriminating attributes."""
    return uuid.uuid5(NAMESPACE_OID, f"{first_week}:{weekday}:{start_time}:{subject_id}")


class ParallelBlockCandidateDAO:
    """Data access object for detected parallel block candidates.

    Parallel candidates are computed on every request.
    Not a ``BaseDAO`` subclass: there is no persistent model to operate on.
    """

    def __init__(self, session: DBSession) -> None:
        self.session = session

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_groups(self) -> dict[UUID, set[UUID]]:
        """Return all candidate groups, keyed by ``candidate_group_id``."""
        candidate_blocks = candidate_blocks_cte()

        stmt = (
            select(
                candidate_blocks.c.original_block_id,
                candidate_blocks.c.first_week,
                candidate_blocks.c.group_weekday,
                candidate_blocks.c.group_start_time,
                candidate_blocks.c.group_subject_id,
            )
            .select_from(candidate_blocks)
            .order_by(
                candidate_blocks.c.first_week,
                candidate_blocks.c.group_weekday,
                candidate_blocks.c.group_start_time,
                candidate_blocks.c.group_subject_id,
                candidate_blocks.c.original_block_id,
            )
        )

        rows = self.session.execute(stmt).all()

        groups: defaultdict[tuple, set[UUID]] = defaultdict(set)
        for row in rows:
            key = (row.first_week, row.group_weekday, row.group_start_time, row.group_subject_id)
            groups[key].add(row.original_block_id)

        return {_group_uuid(*key): block_ids for key, block_ids in groups.items()}

    def get_all_groups_with_info(
        self,
        filters: ParallelBlockCandidateFilters | None = None,
    ) -> list[ParallelBlockCandidateDetailResponse]:
        """Return all candidate groups with associated session and degree info."""
        filters = filters or ParallelBlockCandidateFilters()

        candidate_blocks = candidate_blocks_cte()

        first_session_subq = (
            select(
                Session.original_block_id,
                func.min(Session.id).label("session_id"),
            )
            .group_by(Session.original_block_id)
            .subquery()
        )

        stmt = (
            select(
                candidate_blocks.c.first_week,
                candidate_blocks.c.group_weekday,
                candidate_blocks.c.group_start_time,
                candidate_blocks.c.group_subject_id,
                candidate_blocks.c.original_block_id,
                Subject.name.label("subject_name"),
                Session.start_time.label("session_start_time"),
                Session.weekday.label("session_weekday"),
                Session.duration.label("session_duration"),
                Session.week.label("session_week"),
                Session.type.label("session_type"),
                func.group_concat(Class.code).label("class_codes"),
                Year.number.label("year"),
                Degree.id.label("degree_id"),
                Degree.name.label("degree_name"),
                Degree.acronym.label("degree_acronym"),
            )
            .select_from(candidate_blocks)
            .join(
                first_session_subq,
                first_session_subq.c.original_block_id == candidate_blocks.c.original_block_id,
            )
            .join(Session, Session.id == first_session_subq.c.session_id)
            .join(
                SessionClassSubject,
                (SessionClassSubject.session_id == first_session_subq.c.session_id)
                & (SessionClassSubject.subject_id == candidate_blocks.c.group_subject_id),
            )
            .join(Subject, Subject.id == SessionClassSubject.subject_id)
            .join(Class, Class.id == SessionClassSubject.class_id)
            .join(Year, Year.id == Class.year_id)
            .join(Degree, Degree.id == Year.degree_id)
            .group_by(
                candidate_blocks.c.first_week,
                candidate_blocks.c.group_weekday,
                candidate_blocks.c.group_start_time,
                candidate_blocks.c.group_subject_id,
                candidate_blocks.c.original_block_id,
                Subject.name,
                Session.start_time,
                Session.weekday,
                Session.duration,
                Session.week,
                Session.type,
                Year.number,
                Degree.id,
                Degree.name,
                Degree.acronym,
            )
            .order_by(
                candidate_blocks.c.first_week,
                candidate_blocks.c.group_weekday,
                candidate_blocks.c.group_start_time,
                candidate_blocks.c.group_subject_id,
                candidate_blocks.c.original_block_id,
            )
        )

        if filters.year_id:
            stmt = stmt.where(Year.id == filters.year_id)
        if filters.degree_id:
            stmt = stmt.where(Degree.id == filters.degree_id)
        if filters.subject_id:
            stmt = stmt.where(Subject.id == filters.subject_id)

        rows = self.session.execute(stmt).all()

        merged: dict[tuple, ParallelBlockCandidateDetailResponse] = {}
        for row in rows:
            group_key = (
                row.first_week,
                row.group_weekday,
                row.group_start_time,
                row.group_subject_id,
            )
            candidate_group_id = _group_uuid(*group_key)

            session_entry = ParallelBlockCandidateSession(
                original_block_id=row.original_block_id,
                class_codes=[c.strip() for c in row.class_codes.split(",") if c.strip()]
                if row.class_codes
                else [],
                session_type=row.session_type,
            )

            if group_key not in merged:
                merged[group_key] = ParallelBlockCandidateDetailResponse(
                    candidate_group_id=candidate_group_id,
                    sessions=[session_entry],
                    subject_name=row.subject_name,
                    session_start_time=row.session_start_time,
                    session_weekday=row.session_weekday,
                    session_duration=row.session_duration,
                    session_week=row.session_week,
                    year=row.year,
                    degree_id=row.degree_id,
                    degree_name=row.degree_name,
                    degree_acronym=row.degree_acronym,
                )
            else:
                existing_ids = {s.original_block_id for s in merged[group_key].sessions}
                if row.original_block_id not in existing_ids:
                    merged[group_key].sessions.append(session_entry)

        return list(merged.values())
