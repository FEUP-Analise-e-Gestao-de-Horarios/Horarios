import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import session_teachers

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session, TeacherRedBlock


class Teacher(Base):
    __tablename__ = "teachers"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    number: Mapped[int] = mapped_column(unique=True)
    acronym: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)

    # Relationships
    red_blocks: Mapped[list[TeacherRedBlock]] = relationship(back_populates="teacher")
    sessions: Mapped[list[Session]] = relationship(
        secondary=session_teachers,
        back_populates="teachers",
    )

    def __str__(self) -> str:
        return f"Teacher({self.acronym!r} - {self.name!r})"

    __repr__ = __str__
