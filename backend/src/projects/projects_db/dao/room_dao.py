from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import session_rooms
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.room_red_block import RoomRedBlock
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.schemas.room import RoomStats


class RoomDAO(BaseDAO[Room]):
    """Data access object for Room records."""

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(Room, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(
        self,
        *,
        name: str,
        type: str | None = None,
        size: str | None = None,
        seats: str | None = None,
    ) -> Room:
        """Create and persist a new room.

        Args:
            name: Unique display name of the room.
            type: Optional room type (e.g. "Laboratório", "Anfiteatro").
            size: Optional room size descriptor.
            seats: Optional seating capacity descriptor.

        Returns:
            The newly created Room instance, flushed to the session.
        """
        return self._create(name=name, type=type, size=size, seats=seats)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[RoomStats]:
        """Return all rooms with their session and red-block counts.

        Counts are computed via subqueries and default to 0 when a room has
        no sessions or red blocks.

        Returns:
            A list of RoomStats, one per room, in an unspecified order.
        """
        sessions_sq = (
            select(session_rooms.c.room_id, func.count(SessionModel.id).label("cnt"))
            .join(SessionModel, SessionModel.id == session_rooms.c.session_id)
            .group_by(session_rooms.c.room_id)
            .subquery()
        )
        red_blocks_sq = (
            select(RoomRedBlock.room_id, func.count(RoomRedBlock.id).label("cnt"))
            .group_by(RoomRedBlock.room_id)
            .subquery()
        )

        rows = self.session.execute(
            select(
                Room.id,
                Room.name,
                Room.type,
                Room.size,
                Room.seats,
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
                func.coalesce(red_blocks_sq.c.cnt, 0).label("red_blocks"),
            )
            .outerjoin(sessions_sq, sessions_sq.c.room_id == Room.id)
            .outerjoin(red_blocks_sq, red_blocks_sq.c.room_id == Room.id),
        ).all()

        return [RoomStats.model_validate(row, from_attributes=True) for row in rows]
