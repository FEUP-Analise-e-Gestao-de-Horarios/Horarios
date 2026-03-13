import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import ClassRedBlock, Session, Year
from src.projects.projects_db.models.session import session_classes


class Class(Base):
    __tablename__ = "classes"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id"))

    # Data
    code: Mapped[str] = mapped_column(Text)
    shift: Mapped[int] = mapped_column()

    # Relationships
    year: Mapped[Year] = relationship(back_populates="classes")
    red_blocks: Mapped[list[ClassRedBlock]] = relationship(back_populates="class_")
    sessions: Mapped[list[Session]] = relationship(
        secondary=session_classes,
        back_populates="classes",
    )
