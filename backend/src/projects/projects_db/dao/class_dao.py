from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year


class ClassDAO(BaseDAO[Class]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(Class, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, year_id: UUID, code: str, shift: int) -> Class:
        return self._create(year_id=year_id, code=code, shift=shift)

    # -------------------------------------------------------------------
    # -- Get Classes
    # -------------------------------------------------------------------

    def get(self, class_id: UUID) -> Class | None:
        return self.session.scalars(
            select(Class).where(Class.id == class_id),
        ).one_or_none()

    def get_by_code(self, code: str) -> Class | None:
        return self.session.scalars(
            select(Class).where(Class.code == code),
        ).one_or_none()

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

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_subjects(self, class_id: UUID) -> list[Subject]:
        return list(
            self.session.scalars(
                select(Subject)
                .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
                .where(SessionClassSubject.class_id == class_id)
                .distinct(),
            ).all(),
        )

    def get_sessions(self, class_id: UUID) -> list[Session]:
        return list(
            self.session.scalars(
                select(Session)
                .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                .where(SessionClassSubject.class_id == class_id)
                .distinct(),
            ).all(),
        )
