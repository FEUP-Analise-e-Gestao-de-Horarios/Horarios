from uuid import UUID

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ConflictClass(Base):
    __tablename__ = "conflict_classes"

    conflict_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        ForeignKey("conflicts.conflict_id"),
        primary_key=True,
    )
    class_id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True)
