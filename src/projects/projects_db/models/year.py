import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import Class, Degree, Subject


class Year(Base):
    __tablename__ = "years"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    degree_id: Mapped[UUID] = mapped_column(ForeignKey("degrees.id"))

    # Data
    number: Mapped[int] = mapped_column()

    # Relationships
    degree: Mapped[Degree] = relationship(back_populates="years")
    subjects: Mapped[list[Subject]] = relationship(back_populates="year")
    classes: Mapped[list[Class]] = relationship(back_populates="year")
