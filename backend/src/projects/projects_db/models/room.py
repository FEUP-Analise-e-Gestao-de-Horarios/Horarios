import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import session_rooms

if TYPE_CHECKING:
    from src.projects.projects_db.models import RoomRedBlock, Session


class Room(Base):
    """A physical space where sessions take place."""

    __tablename__ = "rooms"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    name: Mapped[str] = mapped_column(Text, unique=True, index=True)
    type: Mapped[str | None] = mapped_column(Text, index=True)
    size: Mapped[str | None] = mapped_column(Text)
    seats: Mapped[str | None] = mapped_column(Text)

    # Relationships
    red_blocks: Mapped[list[RoomRedBlock]] = relationship(back_populates="room")
    sessions: Mapped[list[Session]] = relationship(secondary=session_rooms, back_populates="rooms")

    def __str__(self) -> str:
        return f"Room({self.name!r})"

    __repr__ = __str__
