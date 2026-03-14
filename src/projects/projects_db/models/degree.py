import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base

if TYPE_CHECKING:
    from src.projects.projects_db.models import Year


class Degree(Base):
    __tablename__ = "degrees"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    acronym: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)

    # Relationships
    years: Mapped[list[Year]] = relationship(back_populates="degree")
