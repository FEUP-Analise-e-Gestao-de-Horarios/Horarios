import uuid
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.schemas.weekday import WeekDay


class TeacherRedBlock(Base):
    """A time slot marked as unavailable for a teacher."""

    __tablename__ = "teacher_red_blocks"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("teachers.id"))

    # Data
    hour: Mapped[int] = mapped_column()
    weekday: Mapped[WeekDay] = mapped_column(Enum(WeekDay, native_enum=False))

    # Relationships
    teacher: Mapped[Teacher] = relationship(back_populates="red_blocks")

    def __str__(self) -> str:
        return f"TeacherRedBlock(teacher_id={self.teacher_id}, {self.weekday} hour={self.hour})"

    __repr__ = __str__
