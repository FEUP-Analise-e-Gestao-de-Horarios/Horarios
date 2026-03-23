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
        """Create a new session with its many-to-many associations.

        Args:
            week: The date representing the week of the session.
            weekday: The day of the week the session takes place.
            start_time: The starting timeslot of the session.
            duration: The duration of the session in timeslot units.
            type_: The session type (e.g. "T", "TP", "PL").
            original_block_id: UUID of the originating timetable block.
            subject_ids: UUIDs of subjects to associate with this session.
            teacher_ids: UUIDs of teachers to associate with this session.
            class_ids: UUIDs of classes to associate with this session.
            room_ids: UUIDs of rooms to associate with this session.

        Returns:
            The newly created Session instance, flushed to the session.
        """
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

    def get_by_teacher(self, teacher_id: UUID) -> list[Session]:
        """Return all sessions taught by the given teacher.

        Args:
            teacher_id: UUID of the teacher to filter by.

        Returns:
            List of Session instances, in an unspecified order.
        """
        return list(
            self.session.scalars(
                select(Session)
                .join(session_teachers, session_teachers.c.session_id == Session.id)
                .where(session_teachers.c.teacher_id == teacher_id),
            ).all(),
        )

    def get_by_room(self, room_id: UUID) -> list[Session]:
        """Return all sessions that take place in the given room.

        Args:
            room_id: UUID of the room to filter by.

        Returns:
            List of Session instances, in an unspecified order.
        """
        return list(
            self.session.scalars(
                select(Session)
                .join(session_rooms, session_rooms.c.session_id == Session.id)
                .where(session_rooms.c.room_id == room_id),
            ).all(),
        )

    def get_by_subject_type(
        self,
        subject: Subject,
        type_: str,
    ) -> Sequence[Session]:
        """Return all sessions for a given subject and session type.

        Args:
            subject: The Subject instance to filter by.
            type_: The session type to filter by (e.g. "T", "TP", "PL").

        Returns:
            A sequence of matching Session instances.
        """
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
        """Find a session by its week, weekday, start time, and class.

        Args:
            week: The date representing the week of the session.
            weekday: The day of the week.
            start_time: The starting timeslot.
            class_id: UUID of the class to filter by.

        Returns:
            The matching Session instance, or None if not found.
        """
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
        """Find a session by its week and originating timetable block.

        Args:
            week: The date representing the week of the session.
            original_block_id: UUID of the originating timetable block.

        Returns:
            The matching Session instance, or None if not found.
        """
        query = select(Session).where(
            Session.week == week,
            Session.original_block_id == original_block_id,
        )
        return self.session.scalars(query).one_or_none()

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
