import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.schemas.weekday import WeekDay

if TYPE_CHECKING:
    from src.projects.projects_db.models import Room


class RoomRedBlock(Base):
    __tablename__ = "room_red_blocks"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id"))

    # Data
    hour: Mapped[int] = mapped_column()
    weekday: Mapped[WeekDay] = mapped_column(Enum(WeekDay, native_enum=False))

    # Relationships
    room: Mapped[Room] = relationship(back_populates="red_blocks")
