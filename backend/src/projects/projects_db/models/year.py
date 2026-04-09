import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base

if TYPE_CHECKING:
    from src.projects.projects_db.models import Class, Degree, Subject


class Year(Base):
    """An academic year within a degree (e.g. 1st year of LEI)."""

    __tablename__ = "years"
    __table_args__ = (UniqueConstraint("degree_id", "number"),)

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    degree_id: Mapped[UUID] = mapped_column(ForeignKey("degrees.id"))

    # Data
    number: Mapped[int] = mapped_column()

    # Relationships
    degree: Mapped[Degree] = relationship(back_populates="years")
    subjects: Mapped[list[Subject]] = relationship(back_populates="year")
    classes: Mapped[list[Class]] = relationship(back_populates="year")

    def __str__(self) -> str:
        return f"Year(degree_id={self.degree_id}, number={self.number})"

    __repr__ = __str__
