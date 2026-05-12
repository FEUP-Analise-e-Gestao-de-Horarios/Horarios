from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.session_class_subject import SessionClassSubject


class SessionClassSubjectDAO(BaseDAO[SessionClassSubject]):
    """Data access object for SessionClassSubject junction records."""

    def __init__(self, session: DBSession) -> None:
        super().__init__(SessionClassSubject, session)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_session(self, session_id: UUID) -> list[SessionClassSubject]:
        """Return all class-subject links for the given session."""
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.session_id == session_id),
            ).all(),
        )
