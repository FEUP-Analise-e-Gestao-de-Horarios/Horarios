from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import session_classes
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

    def get_all_with_stats(self) -> list[ClassStats]:
        sessions_sq = (
            select(session_classes.c.class_id, func.count(SessionModel.id).label("cnt"))
            .join(SessionModel, SessionModel.id == session_classes.c.session_id)
            .group_by(session_classes.c.class_id)
            .subquery()
        )

        rows = self.session.execute(
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
            .outerjoin(sessions_sq, sessions_sq.c.class_id == Class.id),
        ).all()

        return [
            ClassStats(
                id=row.id,
                code=row.code,
                shift=row.shift,
                year_id=row.year_id,
                year_number=row.year_number,
                degree_id=row.degree_id,
                degree_acronym=row.degree_acronym,
                degree_name=row.degree_name,
                num_sessions=row.num_sessions,
            )
            for row in rows
        ]

    def get_by_degree_and_year(self, *, degree_acronym: str, year_number: int) -> list[Class]:
        return list(
            self.session.scalars(
                select(Class)
                .join(Class.year)
                .join(Year.degree)
                .where(Degree.acronym == degree_acronym, Year.number == year_number),
            ).all(),
        )

    def get_by_codes(self, codes: set[str], *, check_count: bool = True) -> list[Class]:
        if not codes:
            return []

        classes = list(self.session.scalars(select(Class).where(Class.code.in_(codes))).all())
        if check_count and len(codes) != len(classes):
            found = {c.code for c in classes}
            missing = codes - found
            raise MultipleNotFoundError("code", missing)

        return classes
