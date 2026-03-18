import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import (
    session_classes,
    session_rooms,
    session_subjects,
    session_teachers,
)
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.schemas.weekday import WeekDay


class SessionDAO(BaseDAO[Session]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(Session, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        duration: int,
        type_: str,
        subject_ids: set[UUID],
        teacher_ids: set[UUID],
        class_ids: set[UUID],
        room_ids: set[UUID],
    ) -> Session:
        session = self._create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type_,
        )

        if subject_ids:
            self.session.execute(
                session_subjects.insert(),
                [{"session_id": session.id, "subject_id": sid} for sid in subject_ids],
            )

        if teacher_ids:
            self.session.execute(
                session_teachers.insert(),
                [{"session_id": session.id, "teacher_id": tid} for tid in teacher_ids],
            )

        if class_ids:
            self.session.execute(
                session_classes.insert(),
                [{"session_id": session.id, "class_id": cid} for cid in class_ids],
            )

        if room_ids:
            self.session.execute(
                session_rooms.insert(),
                [{"session_id": session.id, "room_id": rid} for rid in room_ids],
            )

        return session

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_subject_type(
        self,
        subject: Subject,
        type_: str,
    ) -> Sequence[Session]:
        return self.session.scalars(
            select(Session)
            .join(Session.classes)
            .where(
                and_(
                    Session.subjects.contains(subject),
                    Session.type == type_,
                ),
            ),
        ).fetchall()

    def get_by_class_with_attributes(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        class_ids: set[UUID],
    ) -> Session | None:
        query = select(Session).where(
            Session.week == week,
            Session.weekday == weekday,
            Session.start_time == start_time,
            Session.classes.any(Class.id.in_(class_ids)),
        )
        return self.session.scalars(query).one_or_none()

    def has_subject(self, session: Session, subject_code: str) -> bool:
        query = select(Session).where(
            Session.id == session.id,
            Session.subjects.any(Subject.code.in_([subject_code])),
        )

        return self.session.scalar(query) is not None
