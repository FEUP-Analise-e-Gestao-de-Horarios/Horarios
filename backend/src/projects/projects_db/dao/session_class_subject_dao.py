from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.schemas.parallel_classes import ClassInfo, SessionParallelClasses


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

    def get_session_and_class(
        self,
        session_id: UUID,
        class_id: UUID,
    ) -> SessionClassSubject | None:
        return self.session.scalars(
            select(SessionClassSubject).where(
                SessionClassSubject.session_id == session_id,
                SessionClassSubject.class_id == class_id,
            ),
        ).one_or_none()

    def get_parallel_session_ids_by_subject(self, subject_id: UUID) -> list[UUID]:
        return list(
            self.session.scalars(
                select(SessionClassSubject.session_id)
                .select_from(SessionClassSubject)
                .join(Session, Session.id == SessionClassSubject.session_id)
                .where(Session.type != "T")
                .where(SessionClassSubject.subject_id == subject_id)
                .group_by(SessionClassSubject.session_id)
                .having(func.count(SessionClassSubject.class_id.distinct()) > 1),
            ).all(),
        )

    def get_classes_by_session_ids(self, session_ids: list[UUID]) -> list[SessionParallelClasses]:
        rows = self.session.scalars(
            select(SessionClassSubject)
            .where(SessionClassSubject.session_id.in_(session_ids))
            .options(selectinload(SessionClassSubject.class_)),
        ).all()

        result = {}
        for scs in rows:
            result.setdefault(scs.session_id, []).append(
                ClassInfo.model_validate(scs.class_, from_attributes=True),
            )

        return [
            SessionParallelClasses(session=session_id, classes=classes)
            for session_id, classes in result.items()
        ]
