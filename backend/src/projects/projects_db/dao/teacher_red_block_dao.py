from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.teacher_red_block import TeacherRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay


class TeacherRedBlockDAO(BaseDAO[TeacherRedBlock]):
    """Data access object for TeacherRedBlock (teacher unavailability) records."""

    def __init__(self, session: Session, *, flush_on_create: bool = True) -> None:
        super().__init__(TeacherRedBlock, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all(self) -> list[TeacherRedBlock]:
        """Return every teacher red block in the project database."""
        return list(self.session.scalars(select(TeacherRedBlock)).all())

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, teacher_id: UUID, hour: int, weekday: WeekDay) -> TeacherRedBlock:
        """Create and persist a new teacher red block.

        Args:
            teacher_id: UUID of the teacher this red block applies to.
            hour: The hour timeslot that is blocked.
            weekday: The day of the week that is blocked.

        Returns:
            The newly created TeacherRedBlock instance, flushed to the session.
        """
        return self._create(teacher_id=teacher_id, hour=hour, weekday=weekday)
