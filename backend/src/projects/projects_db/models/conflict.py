import uuid
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.tag import Tag


class Conflict(Base):
    __tablename__ = "conflicts"
    __table_args__ = (Index("ix_conflicts_tag_id", "tag_id"),)

    conflict_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
        default=uuid.uuid4,
    )
    tag_id: Mapped[UUID] = mapped_column(Uuid(native_uuid=False), ForeignKey("tags.tag_id"))

    tag: Mapped[Tag] = relationship("Tag")

    def __str__(self) -> str:
        return f"Conflict({self.conflict_id!r})"

    __repr__ = __str__
