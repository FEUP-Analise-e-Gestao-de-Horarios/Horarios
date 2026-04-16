from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.models import (
    Class,
    Degree,
    Session,
    SessionClassSubject,
    Subject,
    Year,
)
from src.projects.projects_db.models.parallel_block_candidate import ParallelBlockCandidate
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateDetailResponse,
    ParallelBlockCandidateFilters,
)


class ParallelBlockCandidateDAO:
    """Data access object for ParallelBlockCandidate records.

    Not a ``BaseDAO`` subclass: ``ParallelBlockCandidate`` has a composite
    primary key, and ``BaseDAO.get`` / ``delete_by_id`` assume a single-UUID
    PK. None of the inherited helpers fit, so this DAO operates on the
    SQLAlchemy ``Session`` directly.
    """

    def __init__(self, session: DBSession) -> None:
        self.session = session

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_groups(self) -> dict[UUID, set[UUID]]:
        """Return all candidate groups, keyed by ``candidate_group_id``."""
        rows = self.session.scalars(
            select(ParallelBlockCandidate).order_by(ParallelBlockCandidate.candidate_group_id),
        ).all()

        groups: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for row in rows:
            groups[row.candidate_group_id].add(row.original_block_id)
        return groups

    def get_all_groups_with_info(
        self,
        filters: ParallelBlockCandidateFilters | None = None,
    ) -> list[ParallelBlockCandidateDetailResponse]:
        """Return all candidate groups with associated info."""

        filters = filters or ParallelBlockCandidateFilters()

        first_session_subq = (
            select(
                Session.original_block_id,
                func.min(Session.id).label("session_id"),
            )
            .group_by(Session.original_block_id)
            .subquery()
        )

        session_subq = (
            select(
                first_session_subq.c.original_block_id,
                first_session_subq.c.session_id,
                Session.start_time,
                Session.weekday,
                Session.duration,
                Session.week,
            )
            .join(Session, Session.id == first_session_subq.c.session_id)
            .subquery()
        )

        class_subq = (
            select(
                SessionClassSubject.session_id,
                SessionClassSubject.subject_id,
                func.group_concat(Class.code).label("class_codes"),
            )
            .join(Class, Class.id == SessionClassSubject.class_id)
            .group_by(SessionClassSubject.session_id, SessionClassSubject.subject_id)
            .subquery()
        )

        stmt = (
            select(
                ParallelBlockCandidate.candidate_group_id,
                ParallelBlockCandidate.original_block_id,
                Subject.name.label("subject_name"),
                session_subq.c.start_time.label("session_start_time"),
                session_subq.c.weekday.label("session_weekday"),
                session_subq.c.duration.label("session_duration"),
                session_subq.c.week.label("session_week"),
                class_subq.c.class_codes.label("class_codes"),
                Year.number.label("year"),
                Degree.name.label("degree_id"),
                Degree.acronym.label("degree_acronym"),
            )
            .join(
                session_subq,
                session_subq.c.original_block_id == ParallelBlockCandidate.original_block_id,
            )
            .join(
                SessionClassSubject,
                SessionClassSubject.session_id == session_subq.c.session_id,
            )
            .join(Subject, Subject.id == SessionClassSubject.subject_id)
            .join(
                Year,
                Year.id == Subject.year_id,
            )
            .join(
                class_subq,
                (class_subq.c.session_id == session_subq.c.session_id)
                & (class_subq.c.subject_id == Subject.id),
            )
            .join(
                Degree,
                Degree.id == Year.degree_id,
            )
        )

        if filters.year_id:
            stmt = stmt.where(Year.id == filters.year_id)

        if filters.degree_id:
            stmt = stmt.where(Degree.id == filters.degree_id)

        if filters.subject_id:
            stmt = stmt.where(Subject.id == filters.subject_id)

        stmt = stmt.order_by(ParallelBlockCandidate.candidate_group_id)

        rows = self.session.execute(stmt).all()

        merged: dict[UUID, ParallelBlockCandidateDetailResponse] = {}
        for row in rows:
            if row.candidate_group_id not in merged:
                merged[row.candidate_group_id] = ParallelBlockCandidateDetailResponse(
                    candidate_group_id=row.candidate_group_id,
                    original_block_ids=[row.original_block_id],
                    subject_name=row.subject_name,
                    session_start_time=row.session_start_time,
                    session_weekday=row.session_weekday,
                    session_duration=row.session_duration,
                    session_week=row.session_week,
                    class_codes=row.class_codes,
                    year=row.year,
                    degree_id=row.degree_id,
                    degree_acronym=row.degree_acronym,
                )
            else:
                if row.original_block_id not in merged[row.candidate_group_id].original_block_ids:
                    merged[row.candidate_group_id].original_block_ids.append(row.original_block_id)
                existing = (
                    set(merged[row.candidate_group_id].class_codes.split(","))
                    if merged[row.candidate_group_id].class_codes
                    else set()
                )
                new = set(row.class_codes.split(",")) if row.class_codes else set()
                merged[row.candidate_group_id].class_codes = ",".join(sorted(existing | new))

        return list(merged.values())
