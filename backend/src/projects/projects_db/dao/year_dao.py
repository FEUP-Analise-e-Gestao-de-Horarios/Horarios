from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.year import Year


class YearDAO(BaseDAO[Year]):
    def __init__(self, session: Session) -> None:
        super().__init__(Year, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, degree_id: UUID, number: int) -> Year:
        return self._create(degree_id=degree_id, number=number)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_degree(self, degree_acronym: str) -> list[Year]:
        return list(
            self.session.scalars(
                select(Year).join(Year.degree).where(Degree.acronym == degree_acronym),
            ).all(),
        )

    def get_by_degree_and_number(self, *, degree_acronym: str, number: int) -> Year | None:
        return self.session.scalars(
            select(Year)
            .join(Year.degree)
            .where(Degree.acronym == degree_acronym, Year.number == number),
        ).first()
