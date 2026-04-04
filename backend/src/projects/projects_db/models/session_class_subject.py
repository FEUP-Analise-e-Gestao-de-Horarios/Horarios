from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.projects.projects_db.base import Base

if TYPE_CHECKING:
    from src.projects.projects_db.models import Class, Session, Subject


class SessionClassSubject(Base):
    """Junction table linking a session to a class and the subject taught in it."""

    __tablename__ = "sessions_classes_subject"
    __table_args__ = (UniqueConstraint("session_id", "class_id", name="uq_session_class"),)

    # UUIDs
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id"), primary_key=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("subjects.id"), primary_key=True)

    # Relationships
    session: Mapped[Session] = relationship(back_populates="session_class_subjects")
    class_: Mapped[Class] = relationship(back_populates="session_class_subjects")
    subject: Mapped[Subject] = relationship(back_populates="session_class_subjects")
