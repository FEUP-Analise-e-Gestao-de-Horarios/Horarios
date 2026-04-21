from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import session_teachers
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.schemas.teacher import TeacherStats


class TeacherDAO(BaseDAO[Teacher]):
    """Data access object for Teacher records."""

    def __init__(self, session: Session, *, flush_on_create: bool = True) -> None:
        super().__init__(Teacher, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, number: int, acronym: str, name: str) -> Teacher:
        """Create and persist a new teacher.

        Args:
            number: Unique institutional number of the teacher.
            acronym: Short abbreviation identifying the teacher.
            name: Full name of the teacher.

        Returns:
            The newly created Teacher instance, flushed to the session.
        """
        return self._create(number=number, acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[TeacherStats]:
        """Return all teachers with their subject, class, and session counts.

        Counts are computed via subqueries and default to 0 when a teacher
        has no associated records.

        Returns:
            A list of TeacherStats, one per teacher, in an unspecified order.
        """
        subjects_sq = (
            select(
                session_teachers.c.teacher_id,
                func.count(SessionClassSubject.subject_id.distinct()).label("cnt"),
            )
            .join(
                SessionClassSubject,
                SessionClassSubject.session_id == session_teachers.c.session_id,
            )
            .group_by(session_teachers.c.teacher_id)
            .subquery()
        )
        classes_sq = (
            select(
                session_teachers.c.teacher_id,
                func.count(SessionClassSubject.class_id.distinct()).label("cnt"),
            )
            .join(
                SessionClassSubject,
                SessionClassSubject.session_id == session_teachers.c.session_id,
            )
            .group_by(session_teachers.c.teacher_id)
            .subquery()
        )
        sessions_sq = (
            select(session_teachers.c.teacher_id, func.count(SessionModel.id).label("cnt"))
            .join(SessionModel, SessionModel.id == session_teachers.c.session_id)
            .group_by(session_teachers.c.teacher_id)
            .subquery()
        )

        rows = self.session.execute(
            select(
                Teacher.id,
                Teacher.number,
                Teacher.acronym,
                Teacher.name,
                func.coalesce(subjects_sq.c.cnt, 0).label("subjects"),
                func.coalesce(classes_sq.c.cnt, 0).label("classes"),
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
            )
            .outerjoin(subjects_sq, subjects_sq.c.teacher_id == Teacher.id)
            .outerjoin(classes_sq, classes_sq.c.teacher_id == Teacher.id)
            .outerjoin(sessions_sq, sessions_sq.c.teacher_id == Teacher.id),
        ).all()

        return [TeacherStats.model_validate(row, from_attributes=True) for row in rows]
