from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import session_classes, session_teachers
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.class_ import ClassStats


class ClassDAO(BaseDAO[Class]):
    def __init__(self, session: Session) -> None:
        super().__init__(Class, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, year_id: UUID, code: str, shift: int) -> Class:
        return self._create(year_id=year_id, code=code, shift=shift)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_code(self, code: str) -> Class | None:
        return self.session.scalars(
            select(Class).where(Class.code == code),
        ).one_or_none()

    def get_by_codes(self, codes: set[str], *, check_count: bool = True) -> list[Class]:
        if not codes:
            return []

        classes = list(self.session.scalars(select(Class).where(Class.code.in_(codes))).all())
        if check_count and len(codes) != len(classes):
            found = {c.code for c in classes}
            missing = codes - found
            raise MultipleNotFoundError("code", missing)

        return classes

    def get_by_year_with_stats(self, year_id: UUID) -> list[ClassStats]:
        sessions_sq = (
            select(session_classes.c.class_id, func.count(SessionModel.id).label("cnt"))
            .join(SessionModel, SessionModel.id == session_classes.c.session_id)
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
                func.coalesce(sessions_sq.c.cnt, 0).label("num_sessions"),
            )
            .join(Year, Year.id == Class.year_id)
            .join(Degree, Degree.id == Year.degree_id)
            .outerjoin(sessions_sq, sessions_sq.c.class_id == Class.id)
            .where(Class.year_id == year_id)
        )

        rows = self.session.execute(stmt).all()

        return [ClassStats.model_validate(row, from_attributes=True) for row in rows]

    def get_by_teacher(self, teacher_id: UUID) -> list[Class]:
        """Return distinct classes taught by the given teacher across all their sessions."""
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
