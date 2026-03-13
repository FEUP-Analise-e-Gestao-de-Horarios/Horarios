import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models.teacher import Teacher


class TeacherRedBlock(Base):
    __tablename__ = "teacher_red_blocks"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("teachers.id"))

    # Data
    hour: Mapped[int] = mapped_column()
    weekday: Mapped[str] = mapped_column(Text)

    # Relationships
    teacher: Mapped[Teacher] = relationship(back_populates="red_blocks")
