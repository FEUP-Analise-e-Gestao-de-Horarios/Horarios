import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import RoomRedBlock, Session

from ._secondary_tables import session_rooms


class Room(Base):
    __tablename__ = "rooms"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)

    # Data
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    size: Mapped[str | None] = mapped_column(Text)
    seats: Mapped[str | None] = mapped_column(Text)

    # Relationships
    red_blocks: Mapped[list[RoomRedBlock]] = relationship(back_populates="room")
    sessions: Mapped[list[Session]] = relationship(secondary=session_rooms, back_populates="rooms")
