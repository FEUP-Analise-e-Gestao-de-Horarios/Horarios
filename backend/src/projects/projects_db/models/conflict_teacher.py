from uuid import UUID

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ConflictTeacher(Base):
    __tablename__ = "conflict_teachers"

    conflict_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        ForeignKey("conflicts.conflict_id"),
        primary_key=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True)
