import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import Room


class RoomRedBlock(Base):
    __tablename__ = "room_red_blocks"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id"))

    # Data
    hour: Mapped[int] = mapped_column()
    weekday: Mapped[str] = mapped_column(Text)

    # Relationships
    room: Mapped[Room] = relationship(back_populates="red_blocks")
