import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models._secondary_tables import subject_years

if TYPE_CHECKING:
    from src.projects.projects_db.models import SessionClassSubject, Year


class Subject(Base):
    """A unit of study (UC) that students attend sessions of.

    A subject can be taught across several academic years (e.g. shared or
    optional UCs), so its year membership is a many-to-many relationship.
    """

    __tablename__ = "subjects"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    number: Mapped[int] = mapped_column(unique=True, index=True)
    code: Mapped[str] = mapped_column(Text, unique=True, index=True)
    acronym: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)

    # Relationships
    years: Mapped[list[Year]] = relationship(
        secondary=subject_years,
        back_populates="subjects",
    )
    session_class_subjects: Mapped[list[SessionClassSubject]] = relationship(
        back_populates="subject",
    )

    def __str__(self) -> str:
        return f"Subject({self.code!r} - {self.name!r})"

    __repr__ = __str__
