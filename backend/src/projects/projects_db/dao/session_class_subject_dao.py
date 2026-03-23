from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject


class SessionClassSubjectDAO(BaseDAO[SessionClassSubject]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(SessionClassSubject, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, session_id: UUID, class_id: UUID, subject_id: UUID) -> SessionClassSubject:
        return self._create(session_id=session_id, class_id=class_id, subject_id=subject_id)

    # -------------------------------------------------------------------
    # -- Get SessionClassSubjectDAO
    # -------------------------------------------------------------------

    def get(self, session_id: UUID, class_id: UUID, subject_id: UUID) -> SessionClassSubject | None:
        return self.session.scalars(
            select(SessionClassSubject).where(
                SessionClassSubject.session_id == session_id,
                SessionClassSubject.class_id == class_id,
                SessionClassSubject.subject_id == subject_id,
            ),
        ).one_or_none()

    def get_by_session(self, session_id: UUID) -> list[SessionClassSubject]:
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.session_id == session_id),
            ).all(),
        )

    def get_by_class(self, class_id: UUID) -> list[SessionClassSubject]:
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.class_id == class_id),
            ).all(),
        )

    def get_by_subject(self, subject_id: UUID) -> list[SessionClassSubject]:
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.subject_id == subject_id),
            ).all(),
        )

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_subject_by_session_and_class(self, session_id: UUID, class_id: UUID) -> Subject | None:
        return self.session.scalars(
            select(Subject)
            .join(SessionClassSubject)
            .where(
                SessionClassSubject.session_id == session_id,
                SessionClassSubject.class_id == class_id,
            ),
        ).one_or_none()
