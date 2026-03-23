from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models import (
    Class,
    Degree,
    Session,
    SessionClassSubject,
    Subject,
    Year,
)
from src.projects.projects_db.models._secondary_tables import session_teachers
from src.projects.projects_db.schemas.subject import SubjectStats


class SubjectDAO(BaseDAO[Subject]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(Subject, session)

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

    def get(self, subject_id: UUID) -> Subject | None:
        return self.session.scalars(select(Subject).where(Subject.id == subject_id)).one_or_none()

    def get_by_number(self, number: int) -> Subject | None:
        """Retrieve a single subject by its institutional number.

        Args:
            number: The subject number to look up.

        Returns:
            The matching Subject instance, or None if not found.
        """
        return self.session.scalars(select(Subject).where(Subject.number == number)).one_or_none()

    def get_by_numbers(self, numbers: set[int], *, check_count: bool = True) -> list[Subject]:
        """Return subjects matching the given institutional numbers.

        Args:
            numbers: Set of subject numbers to fetch.
            check_count: When True, raises if any number has no matching subject.

        Returns:
            List of Subject instances corresponding to the requested numbers.

        Raises:
            MultipleNotFoundError: If check_count is True and one or more
                numbers have no matching subject.
        """
        if not numbers:
            return []

        subjects = list(
            self.session.scalars(select(Subject).where(Subject.number.in_(numbers))).all(),
        )
        if check_count and len(numbers) != len(subjects):
            found = {s.number for s in subjects}
            missing = numbers - found
            raise MultipleNotFoundError("number", missing)

        return subjects

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

    def get_by_year_with_stats(self, year_id: UUID) -> list[SubjectStats]:
        """Return all subjects for a year with their session counts and degree info.

        Args:
            year_id: UUID of the year to filter subjects by.

        Returns:
            A list of SubjectStats, one per subject in the given year.
        """
        sessions_sq = (
            select(SessionClassSubject.subject_id, func.count(Session.id).label("cnt"))
            .join(Session, Session.id == SessionClassSubject.session_id)
            .group_by(SessionClassSubject.subject_id)
            .subquery()
        )

        stmt = (
            select(
                Subject.id,
                Subject.number,
                Subject.code,
                Subject.acronym,
                Subject.name,
                Year.id.label("year_id"),
                Year.number.label("year_number"),
                Degree.id.label("degree_id"),
                Degree.acronym.label("degree_acronym"),
                Degree.name.label("degree_name"),
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
            )
            .join(Year, Year.id == Subject.year_id)
            .join(Degree, Degree.id == Year.degree_id)
            .outerjoin(sessions_sq, sessions_sq.c.subject_id == Subject.id)
            .where(Subject.year_id == year_id)
        )

        rows = self.session.execute(stmt).all()

        return [SubjectStats.model_validate(row, from_attributes=True) for row in rows]

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_classes(self, subject_id: UUID) -> list[Class]:
        return list(
            self.session.scalars(
                select(Class)
                .join(SessionClassSubject, SessionClassSubject.class_id == Class.id)
                .where(SessionClassSubject.subject_id == subject_id)
                .distinct(),
            ).all(),
        )

    def get_sessions(self, subject_id: UUID) -> list[Session]:
        return list(
            self.session.scalars(
                select(Session)
                .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                .where(SessionClassSubject.subject_id == subject_id)
                .distinct(),
            ).all(),
        )
