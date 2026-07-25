from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base
from src.projects.projects_db.models.session import Session


class ModifiedSession(Base):
    """Cached export order for a session with detected modifications."""

    __tablename__ = "modified_sessions"
    __table_args__ = (
        Index("ix_modified_sessions_session_id", "session_id"),
        Index("ix_modified_sessions_modification_number", "modification_number"),
    )

    modification_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
    )
    step_type: Mapped[str] = mapped_column(Text)
    step_key: Mapped[str] = mapped_column(Text)
    step_payload: Mapped[str] = mapped_column(Text)

    session: Mapped[Session] = relationship()

    def __str__(self) -> str:
        return (
            f"ModifiedSession(number={self.modification_number}, "
            f"session_id={self.session_id}, step_type={self.step_type!r})"
        )

    __repr__ = __str__
