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
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, session_id: UUID, class_id: UUID, subject_id: UUID) -> SessionClassSubject:
        """Create and persist a new session-class-subject link."""
        return self._create(session_id=session_id, class_id=class_id, subject_id=subject_id)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get(self, session_id: UUID, class_id: UUID, subject_id: UUID) -> SessionClassSubject | None:
        """Retrieve a junction record by its composite key."""
        return self.session.scalars(
            select(SessionClassSubject).where(
                SessionClassSubject.session_id == session_id,
                SessionClassSubject.class_id == class_id,
                SessionClassSubject.subject_id == subject_id,
            ),
        ).one_or_none()

    def get_by_session(self, session_id: UUID) -> list[SessionClassSubject]:
        """Return all class-subject links for the given session."""
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.session_id == session_id),
            ).all(),
        )

    def get_by_class(self, class_id: UUID) -> list[SessionClassSubject]:
        """Return all session-subject links for the given class."""
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.class_id == class_id),
            ).all(),
        )

    def get_by_subject(self, subject_id: UUID) -> list[SessionClassSubject]:
        """Return all session-class links for the given subject."""
        return list(
            self.session.scalars(
                select(SessionClassSubject).where(SessionClassSubject.subject_id == subject_id),
            ).all(),
        )
