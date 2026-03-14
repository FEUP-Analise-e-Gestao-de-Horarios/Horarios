import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import session_subjects

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session, Year


class Subject(Base):
    __tablename__ = "subjects"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id"))

    # Data
    number: Mapped[int] = mapped_column(unique=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    acronym: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)

    # Relationships
    year: Mapped[Year] = relationship(back_populates="subjects")
    sessions: Mapped[list[Session]] = relationship(
        secondary=session_subjects,
        back_populates="subjects",
    )
