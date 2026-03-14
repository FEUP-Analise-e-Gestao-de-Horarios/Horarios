from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.teacher import Teacher


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

    def get_by_number(self, number: int) -> Teacher | None:
        return self.session.scalars(select(Teacher).where(Teacher.number == number)).first()

    def get_by_acronym(self, acronym: str) -> Teacher | None:
        return self.session.scalars(select(Teacher).where(Teacher.acronym == acronym)).first()
