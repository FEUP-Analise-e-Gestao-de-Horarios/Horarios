import uuid
from uuid import UUID

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models._secondary_tables import conflict_tags
from src.projects.projects_db.models.tag import Tag


class Conflict(Base):
    __tablename__ = "conflicts"

    conflict_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
        default=uuid.uuid4,
    )

    tags: Mapped[list[Tag]] = relationship("Tag", secondary=conflict_tags)

    def __str__(self) -> str:
        return f"Conflict({self.conflict_id!r})"

    __repr__ = __str__
