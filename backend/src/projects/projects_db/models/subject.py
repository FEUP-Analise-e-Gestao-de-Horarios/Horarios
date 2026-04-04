import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base

if TYPE_CHECKING:
    from src.projects.projects_db.models import SessionClassSubject, Year


class Subject(Base):
    """A unit of study (UC) that students attend sessions of."""

    __tablename__ = "subjects"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id"), index=True)

    # Data
    number: Mapped[int] = mapped_column(unique=True, index=True)
    code: Mapped[str] = mapped_column(Text, unique=True, index=True)
    acronym: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)

    # Relationships
    year: Mapped[Year] = relationship(back_populates="subjects")
    session_class_subjects: Mapped[list[SessionClassSubject]] = relationship(
        back_populates="subject",
    )

    def __str__(self) -> str:
        return f"Subject({self.code!r} - {self.name!r})"

    __repr__ = __str__
