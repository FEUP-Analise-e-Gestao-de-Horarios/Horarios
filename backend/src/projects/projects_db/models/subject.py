import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import sessions_classes_subject

if TYPE_CHECKING:
    from src.projects.projects_db.models import Class, Session, Year


class Subject(Base):
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

    sessions: Mapped[list[Session]] = relationship(
        secondary=sessions_classes_subject,
        primaryjoin="subjects.id == sessions_classes_subject.c.subject_id",
        secondaryjoin="sessions.id == sessions_classes_subject.c.session_id",
        back_populates="subjects",
    )
    classes: Mapped[list[Class]] = relationship(
        secondary=sessions_classes_subject,
        primaryjoin="subjects.id == sessions_classes_subject.c.subject_id",
        secondaryjoin="classes.id == sessions_classes_subject.c.class_id",
        back_populates="subjects",
    )

    def __str__(self) -> str:
        return f"Subject({self.code!r} - {self.name!r})"

    __repr__ = __str__
