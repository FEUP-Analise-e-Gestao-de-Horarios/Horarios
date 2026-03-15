import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.schemas.weekday import WeekDay


class SessionDAO(BaseDAO[SessionModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(SessionModel, session)

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
        type: str,
        room_ids: list[UUID] | None = None,
        teacher_ids: list[UUID] | None = None,
        subject_ids: list[UUID] | None = None,
        class_ids: list[UUID] | None = None,
    ) -> SessionModel:
        session = self._create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type,
        )

        if room_ids:
            session.rooms = list(
                self.session.scalars(
                    select(Room).where(Room.id.in_(room_ids)),
                ).all(),
            )

        if teacher_ids:
            session.teachers = list(
                self.session.scalars(
                    select(Teacher).where(Teacher.id.in_(teacher_ids)),
                ).all(),
            )

        if subject_ids:
            session.subjects = list(
                self.session.scalars(
                    select(Subject).where(Subject.id.in_(subject_ids)),
                ).all(),
            )

        if class_ids:
            session.classes = list(
                self.session.scalars(
                    select(Class).where(Class.id.in_(class_ids)),
                ).all(),
            )

        return session

    def create_if_not_exists(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        duration: int,
        type: str,
        room_ids: list[UUID] | None = None,
        teacher_ids: list[UUID] | None = None,
        subject_ids: list[UUID] | None = None,
        class_ids: list[UUID] | None = None,
    ) -> SessionModel:
        # 1. Check if a session with these core unique constraints already exists
        existing_stmt = select(SessionModel).filter_by(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type,
        )

        existing_session = self.session.execute(existing_stmt).scalar_one_or_none()

        if existing_session is not None:
            return existing_session

        # 2. If it doesn't exist, proceed with your existing creation logic
        return self.create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type,
            room_ids=room_ids,
            teacher_ids=teacher_ids,
            subject_ids=subject_ids,
            class_ids=class_ids,
        )

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_week(self, week: datetime.date) -> list[SessionModel]:
        return list(
            self.session.scalars(
                select(SessionModel).where(SessionModel.week == week),
            ).all(),
        )

    def get_by_room(self, room_id: UUID) -> list[SessionModel]:
        room = self.session.get(Room, room_id)
        return room.sessions if room else []

    def get_by_teacher(self, teacher_id: UUID) -> list[SessionModel]:
        teacher = self.session.get(Teacher, teacher_id)
        return teacher.sessions if teacher else []

    def get_by_subject(self, subject_id: UUID) -> list[SessionModel]:
        subject = self.session.get(Subject, subject_id)
        return subject.sessions if subject else []

    def get_by_class(self, class_id: UUID) -> list[SessionModel]:
        class_ = self.session.get(Class, class_id)
        return class_.sessions if class_ else []
