from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import session_classes, session_teachers
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.class_ import ClassStats


class ClassDAO(BaseDAO[Class]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(Class, session)

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

    def get(self, class_id: UUID) -> Class | None:
        return self.session.scalars(
            select(Class).where(Class.id == class_id),
        ).one_or_none()

    def get_by_code(self, code: str) -> Class | None:
        """Retrieve a single class by its unique code.

        Args:
            code: The class code to look up.

        Returns:
            The matching Class instance, or None if not found.
        """
        return self.session.scalars(
            select(Class).where(Class.code == code),
        ).one_or_none()

    def get_by_codes(self, codes: set[str], *, check_count: bool = True) -> list[Class]:
        """Return classes matching the given codes.

        Args:
            codes: Set of class codes to fetch.
            check_count: When True, raises if any code has no matching class.

        Returns:
            List of Class instances corresponding to the requested codes.

        Raises:
            MultipleNotFoundError: If check_count is True and one or more
                codes have no matching class.
        """
        if not codes:
            return []

        classes = list(self.session.scalars(select(Class).where(Class.code.in_(codes))).all())
        if check_count and len(codes) != len(classes):
            found = {c.code for c in classes}
            missing = codes - found
            raise MultipleNotFoundError("code", missing)

        return classes

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
                .join(session_classes, session_classes.c.class_id == Class.id)
                .join(
                    session_teachers,
                    session_teachers.c.session_id == session_classes.c.session_id,
                )
                .where(session_teachers.c.teacher_id == teacher_id)
                .distinct(),
            ).all(),
        )

    # -------------------------------------------------------------------
    # -- Get Classes with Stats
    # -------------------------------------------------------------------

    def get_by_year_with_stats(self, year_id: UUID) -> list[ClassStats]:
        """Return all classes for a year with their session counts and degree info.

        Args:
            year_id: UUID of the year to filter classes by.

        Returns:
            A list of ClassStats, one per class in the given year.
        """
        sessions_sq = (
            select(session_classes.c.class_id, func.count(Session.id).label("cnt"))
            .join(Session, Session.id == session_classes.c.session_id)
            .group_by(session_classes.c.class_id)
            .subquery()
        )

        stmt = (
            select(
                Class.id,
                Class.code,
                Class.shift,
                Year.id.label("year_id"),
                Year.number.label("year_number"),
                Degree.id.label("degree_id"),
                Degree.acronym.label("degree_acronym"),
                Degree.name.label("degree_name"),
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
            )
            .join(Year, Year.id == Class.year_id)
            .join(Degree, Degree.id == Year.degree_id)
            .outerjoin(sessions_sq, sessions_sq.c.class_id == Class.id)
            .where(Class.year_id == year_id)
        )

        rows = self.session.execute(stmt).all()

        return [ClassStats.model_validate(row, from_attributes=True) for row in rows]

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_subjects(self, class_id: UUID) -> list[Subject]:
        return list(
            self.session.scalars(
                select(Subject)
                .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
                .where(SessionClassSubject.class_id == class_id)
                .distinct(),
            ).all(),
        )

    def get_sessions(self, class_id: UUID) -> list[Session]:
        return list(
            self.session.scalars(
                select(Session)
                .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                .where(SessionClassSubject.class_id == class_id)
                .distinct(),
            ).all(),
        )
