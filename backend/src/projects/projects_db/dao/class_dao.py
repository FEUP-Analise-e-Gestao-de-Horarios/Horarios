from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models import (
    Class,
    SessionClassSubject,
)
from src.projects.projects_db.models._secondary_tables import session_teachers
from src.projects.projects_db.schemas.class_ import ClassStats


class ClassDAO(BaseDAO[Class]):
    """Data access object for Class records."""

    def __init__(self, session: DBSession, *, flush_on_create: bool = True) -> None:
        super().__init__(Class, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, year_id: UUID, code: str, shift: int) -> Class:
        """Create and persist a new class.

        Args:
            year_id: UUID of the year this class belongs to.
            code: Unique code identifying the class.
            shift: Shift number for the class.

        Returns:
            The newly created Class instance, flushed to the session.
        """
        return self._create(year_id=year_id, code=code, shift=shift)

    # -------------------------------------------------------------------
    # -- Get Classes
    # -------------------------------------------------------------------

    def find_missing_in_year(self, year_id: UUID, ids: Iterable[UUID]) -> list[UUID]:
        """Return the subset of ``ids`` not matching a class in the given year.

        Deduplicates the input. Order is not preserved. Treats ids that exist
        but belong to a different year the same as ids that do not exist.
        """
        unique = set(ids)
        if not unique:
            return []
        existing = set(
            self.session.scalars(
                select(Class.id).where(Class.id.in_(unique), Class.year_id == year_id),
            ).all(),
        )
        return list(unique - existing)

    def get_by_teacher(self, teacher_id: UUID) -> list[Class]:
        """Return distinct classes taught by the given teacher across all their sessions.

        Args:
            teacher_id: UUID of the teacher to filter by.

        Returns:
            List of distinct Class instances associated with the teacher.
        """
        return list(
            self.session.scalars(
                select(Class)
                .join(SessionClassSubject, SessionClassSubject.class_id == Class.id)
                .join(
                    session_teachers,
                    session_teachers.c.session_id == SessionClassSubject.session_id,
                )
                .where(session_teachers.c.teacher_id == teacher_id)
                .distinct(),
            ).all(),
        )

    # -------------------------------------------------------------------
    # -- Get Classes with Stats
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[ClassStats]:
        """Return all classes with their session counts.

        Returns:
            A list of ClassStats, one per class, in an unspecified order.
        """
        return self._get_with_stats()

    def get_by_year_with_stats(self, year_id: UUID) -> list[ClassStats]:
        """Return all classes for a year with their session counts.

        Args:
            year_id: UUID of the year to filter classes by.

        Returns:
            A list of ClassStats, one per class in the given year.
        """
        return self._get_with_stats(year_id=year_id)

    def _get_with_stats(self, *, year_id: UUID | None = None) -> list[ClassStats]:
        sessions_sq_q = select(
            SessionClassSubject.class_id,
            func.count(SessionClassSubject.session_id).label("cnt"),
        )
        if year_id is not None:
            sessions_sq_q = sessions_sq_q.join(
                Class,
                Class.id == SessionClassSubject.class_id,
            ).where(Class.year_id == year_id)
        sessions_sq = sessions_sq_q.group_by(SessionClassSubject.class_id).subquery()

        stmt = select(
            Class.id,
            Class.year_id,
            Class.code,
            Class.shift,
            func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
        ).outerjoin(sessions_sq, sessions_sq.c.class_id == Class.id)
        if year_id is not None:
            stmt = stmt.where(Class.year_id == year_id)

        rows = self.session.execute(stmt).all()

        return [ClassStats.model_validate(row, from_attributes=True) for row in rows]
