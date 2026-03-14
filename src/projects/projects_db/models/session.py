import datetime
import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import Date, Enum, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import Class, Room, Subject, Teacher
from src.projects.projects_db.schemas.weekday import WeekDay

from ._secondary_tables import session_classes, session_rooms, session_subjects, session_teachers


class Session(Base):
    __tablename__ = "sessions"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    week: Mapped[datetime.date] = mapped_column(Date)
    weekday: Mapped[WeekDay] = mapped_column(Enum(WeekDay, native_enum=False))
    start_time: Mapped[int] = mapped_column()
    duration: Mapped[int] = mapped_column()
    type: Mapped[str] = mapped_column(Text)

    # Relationships
    rooms: Mapped[list[Room]] = relationship(secondary=session_rooms, back_populates="sessions")
    teachers: Mapped[list[Teacher]] = relationship(
        secondary=session_teachers,
        back_populates="sessions",
    )
    subjects: Mapped[list[Subject]] = relationship(
        secondary=session_subjects,
        back_populates="sessions",
    )
    classes: Mapped[list[Class]] = relationship(
        secondary=session_classes,
        back_populates="sessions",
    )
