from uuid import UUID

from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.class_red_block import ClassRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay


class ClassRedBlockDAO(BaseDAO[ClassRedBlock]):
    """Data access object for ClassRedBlock (class unavailability) records."""

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(ClassRedBlock, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, class_id: UUID, hour: int, weekday: WeekDay) -> ClassRedBlock:
        """Create and persist a new class red block.

        Args:
            class_id: UUID of the class this red block applies to.
            hour: The hour timeslot that is blocked.
            weekday: The day of the week that is blocked.

        Returns:
            The newly created ClassRedBlock instance, flushed to the session.
        """
        return self._create(class_id=class_id, hour=hour, weekday=weekday)
