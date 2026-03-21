from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models._secondary_tables import session_subjects
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.subject import SubjectStats


class SubjectDAO(BaseDAO[Subject]):
    def __init__(self, session: Session) -> None:
        super().__init__(Subject, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, year_id: UUID, number: int, code: str, acronym: str, name: str) -> Subject:
        return self._create(year_id=year_id, number=number, code=code, acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_number(self, number: int) -> Subject | None:
        return self.session.scalars(select(Subject).where(Subject.number == number)).first()

    def get_by_code(self, code: str) -> Subject | None:
        return self.session.scalars(select(Subject).where(Subject.code == code)).one_or_none()

    def get_by_numbers(self, numbers: set[int], *, check_count: bool = True) -> list[Subject]:
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

    def get_by_year_with_stats(self, year_id: UUID) -> list[SubjectStats]:
        return self.get_all_with_stats(year_id=year_id)

    def get_all_with_stats(self, year_id: UUID | None = None) -> list[SubjectStats]:
        sessions_sq = (
            select(session_subjects.c.subject_id, func.count(SessionModel.id).label("cnt"))
            .join(SessionModel, SessionModel.id == session_subjects.c.session_id)
            .group_by(session_subjects.c.subject_id)
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
                func.coalesce(sessions_sq.c.cnt, 0).label("num_sessions"),
            )
            .join(Year, Year.id == Subject.year_id)
            .join(Degree, Degree.id == Year.degree_id)
            .outerjoin(sessions_sq, sessions_sq.c.subject_id == Subject.id)
        )
        if year_id is not None:
            stmt = stmt.where(Subject.year_id == year_id)

        rows = self.session.execute(stmt).all()

        return [
            SubjectStats(
                id=row.id,
                number=row.number,
                code=row.code,
                acronym=row.acronym,
                name=row.name,
                year_id=row.year_id,
                year_number=row.year_number,
                degree_id=row.degree_id,
                degree_acronym=row.degree_acronym,
                degree_name=row.degree_name,
                num_sessions=row.num_sessions,
            )
            for row in rows
        ]

    def get_by_degree_and_year(self, *, degree_acronym: str, year_number: int) -> list[Subject]:
        return list(
            self.session.scalars(
                select(Subject)
                .join(Subject.year)
                .join(Year.degree)
                .where(Degree.acronym == degree_acronym, Year.number == year_number),
            ).all(),
        )
