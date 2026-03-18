from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year


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

    def get_by_degree_and_year(self, *, degree_acronym: str, year_number: int) -> list[Subject]:
        return list(
            self.session.scalars(
                select(Subject)
                .join(Subject.year)
                .join(Year.degree)
                .where(Degree.acronym == degree_acronym, Year.number == year_number),
            ).all(),
        )
