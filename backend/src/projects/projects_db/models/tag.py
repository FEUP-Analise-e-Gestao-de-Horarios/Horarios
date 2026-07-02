import uuid
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    tag_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, unique=True, index=True)

    def __str__(self) -> str:
        return f"Tag({self.name!r})"

    __repr__ = __str__
