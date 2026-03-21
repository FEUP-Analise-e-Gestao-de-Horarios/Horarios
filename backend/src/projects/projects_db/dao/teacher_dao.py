from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import session_teachers
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
                func.coalesce(sessions_sq.c.cnt, 0).label("num_sessions"),
            ).outerjoin(sessions_sq, sessions_sq.c.teacher_id == Teacher.id),
        ).all()

        return [
            TeacherStats(
                id=row.id,
                number=row.number,
                acronym=row.acronym,
                name=row.name,
                num_sessions=row.num_sessions,
            )
            for row in rows
        ]

    def get_by_number(self, number: int) -> Teacher | None:
        return self.session.scalars(select(Teacher).where(Teacher.number == number)).first()

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

    def get_by_acronym(self, acronym: str) -> Teacher | None:
        return self.session.scalars(select(Teacher).where(Teacher.acronym == acronym)).first()
