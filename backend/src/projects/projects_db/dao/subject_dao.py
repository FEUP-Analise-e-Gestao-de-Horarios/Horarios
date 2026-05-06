from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models import (
    SessionClassSubject,
    Subject,
)
from src.projects.projects_db.models._secondary_tables import session_teachers
from src.projects.projects_db.schemas.subject import SubjectStats


class SubjectDAO(BaseDAO[Subject]):
    """Data access object for Subject records."""

    def __init__(self, session: DBSession, flush_on_create: bool = True) -> None:
        super().__init__(Subject, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, year_id: UUID, number: int, code: str, acronym: str, name: str) -> Subject:
        """Create and persist a new subject.

        Args:
            year_id: UUID of the year this subject belongs to.
            number: Unique institutional number of the subject.
            code: Unique code identifying the subject.
            acronym: Short abbreviation for the subject.
            name: Full name of the subject.

        Returns:
            The newly created Subject instance, flushed to the session.
        """
        return self._create(year_id=year_id, number=number, code=code, acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get Subjects
    # -------------------------------------------------------------------

    def find_missing_in_year(self, year_id: UUID, ids: Iterable[UUID]) -> list[UUID]:
        """Return the subset of ``ids`` not matching a subject in the given year.

        Deduplicates the input. Order is not preserved. Treats ids that exist
        but belong to a different year the same as ids that do not exist.
        """
        unique = set(ids)
        if not unique:
            return []
        existing = set(
            self.session.scalars(
                select(Subject.id).where(Subject.id.in_(unique), Subject.year_id == year_id),
            ).all(),
        )
        return list(unique - existing)

    def get_by_teacher(self, teacher_id: UUID) -> list[Subject]:
        """Return distinct subjects taught by the given teacher across all their sessions.

        Args:
            teacher_id: UUID of the teacher to filter by.

        Returns:
            List of distinct Subject instances associated with the teacher.
        """
        return list(
            self.session.scalars(
                select(Subject)
                .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
                .join(
                    session_teachers,
                    session_teachers.c.session_id == SessionClassSubject.session_id,
                )
                .where(session_teachers.c.teacher_id == teacher_id)
                .distinct(),
            ).all(),
        )

    # -------------------------------------------------------------------
    # -- Get Subjects with Stats
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[SubjectStats]:
        """Return all subjects with their session counts.

        Returns:
            A list of SubjectStats, one per subject, in an unspecified order.
        """
        return self._get_with_stats()

    def get_by_year_with_stats(self, year_id: UUID) -> list[SubjectStats]:
        """Return all subjects for a year with their session counts.

        Args:
            year_id: UUID of the year to filter subjects by.

        Returns:
            A list of SubjectStats, one per subject in the given year.
        """
        return self._get_with_stats(year_id=year_id)

    def _get_with_stats(self, *, year_id: UUID | None = None) -> list[SubjectStats]:
        sessions_sq_q = select(
            SessionClassSubject.subject_id,
            func.count(SessionClassSubject.session_id).label("cnt"),
        )
        if year_id is not None:
            sessions_sq_q = sessions_sq_q.join(
                Subject,
                Subject.id == SessionClassSubject.subject_id,
            ).where(Subject.year_id == year_id)
        sessions_sq = sessions_sq_q.group_by(SessionClassSubject.subject_id).subquery()

        stmt = select(
            Subject.id,
            Subject.year_id,
            Subject.number,
            Subject.code,
            Subject.acronym,
            Subject.name,
            func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
        ).outerjoin(sessions_sq, sessions_sq.c.subject_id == Subject.id)
        if year_id is not None:
            stmt = stmt.where(Subject.year_id == year_id)

        rows = self.session.execute(stmt).all()

        return [SubjectStats.model_validate(row, from_attributes=True) for row in rows]
