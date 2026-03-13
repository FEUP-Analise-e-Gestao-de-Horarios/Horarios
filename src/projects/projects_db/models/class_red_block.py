import uuid
from uuid import UUID

from projects_db.base import Base
from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.models import Class


class ClassRedBlock(Base):
    __tablename__ = "class_red_blocks"

    # UUIDs
    id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), primary_key=True, default=uuid.uuid7)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"))

    # Data
    hour: Mapped[int] = mapped_column()
    weekday: Mapped[str] = mapped_column(Text)

    # Relationships
    class_: Mapped[Class] = relationship(back_populates="red_blocks")
