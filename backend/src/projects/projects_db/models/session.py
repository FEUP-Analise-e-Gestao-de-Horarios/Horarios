import datetime
import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, Index, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models._secondary_tables import (
    session_rooms,
    session_teachers,
)
from src.projects.projects_db.schemas.weekday import WeekDay

if TYPE_CHECKING:
    from src.projects.projects_db.models import Room, SessionClassSubject, Teacher


class Session(Base):
    """A single scheduled class event (lecture, lab, seminar, etc.)."""

    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("week", "original_block_id"),
        Index("ix_sessions_week_original_block_id", "week", "original_block_id"),
        Index("ix_sessions_conflict_slot", "week", "weekday", "start_time", "duration", "id"),
        # Covers the per-block min/max(week) lookup in the parallel-candidate
        # query; also serves plain original_block_id filters as a prefix.
        Index("ix_sessions_original_block_id_week", "original_block_id", "week"),
    )

    # UUIDs
    id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
        default=uuid.uuid7,
    )

    # Data
    week: Mapped[datetime.date] = mapped_column(Date, index=True)
    weekday: Mapped[WeekDay] = mapped_column(Enum(WeekDay, native_enum=False))
    start_time: Mapped[int] = mapped_column()
    duration: Mapped[int] = mapped_column()
    type: Mapped[str] = mapped_column(Text, index=True)
    original_block_id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False))

    # Relationships
    rooms: Mapped[list[Room]] = relationship(
        secondary=session_rooms,
        back_populates="sessions",
    )
    teachers: Mapped[list[Teacher]] = relationship(
        secondary=session_teachers,
        back_populates="sessions",
    )
    session_class_subjects: Mapped[list[SessionClassSubject]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return f"Session(week={self.week}, {self.weekday} start={self.start_time}, duration={self.duration}, type={self.type!r})"

    __repr__ = __str__
