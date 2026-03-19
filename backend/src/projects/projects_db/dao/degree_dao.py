from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.degree import Degree


class DegreeDAO(BaseDAO[Degree]):
    def __init__(self, session: Session) -> None:
        super().__init__(Degree, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, acronym: str, name: str) -> Degree:
        return self._create(acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_acronym(self, acronym: str) -> Degree | None:
        return self.session.scalars(select(Degree).where(Degree.acronym == acronym)).first()
