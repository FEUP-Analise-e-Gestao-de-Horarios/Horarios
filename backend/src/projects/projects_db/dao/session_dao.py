import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import (
    session_rooms,
    session_teachers,
)
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
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
        original_block_id: UUID,
        teacher_ids: set[UUID],
        room_ids: set[UUID],
    ) -> Session:
        session = self._create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type_,
            original_block_id=original_block_id,
        )

        if teacher_ids:
            self.session.execute(
                session_teachers.insert(),
                [{"session_id": session.id, "teacher_id": tid} for tid in teacher_ids],
            )

        if room_ids:
            self.session.execute(
                session_rooms.insert(),
                [{"session_id": session.id, "room_id": rid} for rid in room_ids],
            )

        return session

    # -------------------------------------------------------------------
    # -- Get Sessions
    # -------------------------------------------------------------------

    def get(self, session_id: UUID) -> Session | None:
        return self.session.scalars(select(Session).where(Session.id == session_id)).one_or_none()

    def get_by_subject_type(
        self,
        subject: Subject,
        type_: str,
    ) -> Sequence[Session]:
        return self.session.scalars(
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .where(
                SessionClassSubject.subject_id == subject.id,
                Session.type == type_,
            ),
        ).fetchall()

    def get_by_week_weekday_start_time_and_class(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        class_id: UUID,
    ) -> Session | None:
        query = (
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .where(
                Session.week == week,
                Session.weekday == weekday,
                Session.start_time == start_time,
                SessionClassSubject.class_id == class_id,
            )
        )
        return self.session.scalars(query).first()

    def get_by_week_and_block(
        self,
        *,
        week: datetime.date,
        original_block_id: UUID,
    ) -> Session | None:
        query = select(Session).where(
            Session.week == week,
            Session.original_block_id == original_block_id,
        )
        return self.session.scalars(query).one_or_none()

    def has_subject(self, session: Session, subject_code: str) -> bool:
        query = (
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .join(Subject, Subject.id == SessionClassSubject.subject_id)
            .where(
                Session.id == session.id,
                Subject.code == subject_code,
            )
        )
        return self.session.scalar(query) is not None

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_subjects(self, session_id: UUID) -> list[Subject]:
        return list(
            self.session.scalars(
                select(Subject)
                .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
                .where(SessionClassSubject.session_id == session_id)
                .distinct(),
            ).all(),
        )

    def get_classes(self, session_id: UUID) -> list[Class]:
        return list(
            self.session.scalars(
                select(Class)
                .join(SessionClassSubject, SessionClassSubject.class_id == Class.id)
                .where(SessionClassSubject.session_id == session_id)
                .distinct(),
            ).all(),
        )
