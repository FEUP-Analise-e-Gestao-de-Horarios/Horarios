from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.room_red_block import RoomRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay


class RoomRedBlockDAO(BaseDAO[RoomRedBlock]):
    def __init__(self, session: Session) -> None:
        super().__init__(RoomRedBlock, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, room_id: UUID, hour: int, weekday: WeekDay) -> RoomRedBlock:
        """Create and persist a new room red block.

        Args:
            room_id: UUID of the room this red block applies to.
            hour: The hour timeslot that is blocked.
            weekday: The day of the week that is blocked.

        Returns:
            The newly created RoomRedBlock instance, flushed to the session.
        """
        return self._create(room_id=room_id, hour=hour, weekday=weekday)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_room(self, room_id: UUID) -> list[RoomRedBlock]:
        """Return all red blocks for the given room.

        Args:
            room_id: UUID of the room to filter by.

        Returns:
            List of RoomRedBlock instances for the room.
        """
        return list(
            self.session.scalars(
                select(RoomRedBlock).where(RoomRedBlock.room_id == room_id),
            ).all(),
        )
