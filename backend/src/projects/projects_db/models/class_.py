import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base

if TYPE_CHECKING:
    from src.projects.projects_db.models import ClassRedBlock, SessionClassSubject, Year


class Class(Base):
    """A scheduled student class within a degree and year (e.g. ``1LEI1T``)."""

    __tablename__ = "classes"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id"), index=True)

    # Data
    code: Mapped[str] = mapped_column(Text, unique=True, index=True)
    shift: Mapped[int] = mapped_column()

    # Relationships
    year: Mapped[Year] = relationship(back_populates="classes")
    red_blocks: Mapped[list[ClassRedBlock]] = relationship(back_populates="class_")
    session_class_subjects: Mapped[list[SessionClassSubject]] = relationship(
        back_populates="class_",
    )

    def __str__(self) -> str:
        return f"Class(code={self.code!r}, shift={self.shift})"

    __repr__ = __str__
