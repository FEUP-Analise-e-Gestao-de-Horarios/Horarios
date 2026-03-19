import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import sessions_classes_subject

if TYPE_CHECKING:
    from src.projects.projects_db.models import ClassRedBlock, Session, Subject, Year


class Class(Base):
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
    sessions: Mapped[list[Session]] = relationship(
        secondary=sessions_classes_subject,
        primaryjoin="classes.id == sessions_classes_subject.c.class_id",
        secondaryjoin="sessions.id == sessions_classes_subject.c.session_id",
        back_populates="classes",
    )
    subjects: Mapped[list[Subject]] = relationship(
        secondary=sessions_classes_subject,
        primaryjoin="classes.id == sessions_classes_subject.c.class_id",
        secondaryjoin="subjects.id == sessions_classes_subject.c.subject_id",
        back_populates="classes",
    )

    def __str__(self) -> str:
        return f"Class(code={self.code!r}, shift={self.shift})"

    __repr__ = __str__
