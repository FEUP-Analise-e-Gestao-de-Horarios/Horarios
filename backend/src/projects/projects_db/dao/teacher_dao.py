from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import (
    session_classes,
    session_subjects,
    session_teachers,
)
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.schemas.teacher import TeacherStats


class TeacherDAO(BaseDAO[Teacher]):
    def __init__(self, session: Session) -> None:
        super().__init__(Teacher, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, number: int, acronym: str, name: str) -> Teacher:
        return self._create(number=number, acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[TeacherStats]:
        subjects_sq = (
            select(
                session_teachers.c.teacher_id,
                func.count(session_subjects.c.subject_id.distinct()).label("cnt"),
            )
            .join(session_subjects, session_subjects.c.session_id == session_teachers.c.session_id)
            .group_by(session_teachers.c.teacher_id)
            .subquery()
        )
        classes_sq = (
            select(
                session_teachers.c.teacher_id,
                func.count(session_classes.c.class_id.distinct()).label("cnt"),
            )
            .join(session_classes, session_classes.c.session_id == session_teachers.c.session_id)
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

    def get_by_numbers(self, numbers: set[int], *, check_count: bool = True) -> list[Teacher]:
        if not numbers:
            return []

        teachers = list(
            self.session.scalars(select(Teacher).where(Teacher.number.in_(numbers))).all(),
        )
        if check_count and len(numbers) != len(teachers):
            found = {t.number for t in teachers}
            missing = numbers - found
            raise MultipleNotFoundError("number", missing)

        return teachers
