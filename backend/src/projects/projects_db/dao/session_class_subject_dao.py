from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, insert, select
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

    def distinct_subject_ids(self, session_id: UUID) -> set[UUID]:
        """Return the distinct subject ids currently taught by this session."""
        return set(
            self.session.scalars(
                select(SessionClassSubject.subject_id).where(
                    SessionClassSubject.session_id == session_id,
                ),
            ).all(),
        )

    def replace_for_session(
        self,
        session_id: UUID,
        pairs: Sequence[tuple[UUID, UUID]],
    ) -> None:
        """Replace a session's (class, subject) links wholesale.

        Args:
            session_id: The session whose links are being replaced.
            pairs: `(class_id, subject_id)` pairs to link in its place. An
                empty sequence just clears the session's classes/subjects.
        """
        self.session.execute(
            delete(SessionClassSubject).where(SessionClassSubject.session_id == session_id),
        )
        if not pairs:
            return
        self.session.execute(
            insert(SessionClassSubject),
            [
                {"session_id": session_id, "class_id": class_id, "subject_id": subject_id}
                for class_id, subject_id in pairs
            ],
        )
