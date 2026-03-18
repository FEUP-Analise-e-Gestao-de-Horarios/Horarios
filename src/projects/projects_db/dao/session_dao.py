import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select
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
        room_names: list[str] | None = None,
        teacher_ids: list[UUID] | None = None,
        teacher_numbers: list[int] | None = None,
        subject_ids: list[UUID] | None = None,
        subject_codes: list[str] | None = None,
        class_ids: list[UUID] | None = None,
        class_codes: list[str] | None = None,
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
        elif room_names:
            session.rooms = list(
                self.session.scalars(
                    select(Room).where(Room.name.in_(room_names)),
                ).all(),
            )

        if teacher_ids:
            session.teachers = list(
                self.session.scalars(
                    select(Teacher).where(Teacher.id.in_(teacher_ids)),
                ).all(),
            )
        elif teacher_numbers:
            session.teachers = list(
                self.session.scalars(
                    select(Teacher).where(Teacher.number.in_(teacher_numbers)),
                ).all(),
            )

        if subject_ids:
            session.subjects = list(
                self.session.scalars(
                    select(Subject).where(Subject.id.in_(subject_ids)),
                ).all(),
            )
        elif subject_codes:
            session.subjects = list(
                self.session.scalars(
                    select(Subject).where(Subject.code.in_(subject_codes)),
                ).all(),
            )

        if class_ids:
            session.classes = list(
                self.session.scalars(
                    select(Class).where(Class.id.in_(class_ids)),
                ).all(),
            )
        elif class_codes:
            session.classes = list(
                self.session.scalars(
                    select(Class).where(Class.code.in_(class_codes)),
                ).all(),
            )

        return session

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

    def get_by_subject_type(
        self,
        subject: Subject,
        type: str,
    ) -> Sequence[SessionModel]:
        return self.session.scalars(
            select(SessionModel)
            .join(SessionModel.classes)
            .where(
                and_(
                    SessionModel.subjects.contains(subject),
                    SessionModel.type == type,
                ),
            ),
        ).fetchall()

    def get_by_class_with_attributes(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        duration: int,
        type: str,
        class_codes: list[str],
        teacher_numbers: list[int],
        room_names: list[str] | None,
    ) -> SessionModel | None:
        criteria = [
            SessionModel.week == week,
            SessionModel.weekday == weekday,
            SessionModel.start_time == start_time,
            SessionModel.duration == duration,
            SessionModel.type == type,
        ]
        stmt = select(SessionModel).where(
            and_(*criteria),
            SessionModel.classes.any(Class.code.in_(class_codes)),
            SessionModel.teachers.any(Teacher.number.in_(teacher_numbers)),
        )

        if room_names is not None:
            stmt.where(SessionModel.rooms.any(Room.name.in_(room_names)))

        return self.session.scalar(stmt)

    def has_subject(self, session: SessionModel, subject_code: str) -> bool:
        query = select(SessionModel).where(
            SessionModel.id == session.id,
            SessionModel.subjects.any(Subject.code.in_([subject_code])),
        )

        return self.session.scalar(query) is not None
