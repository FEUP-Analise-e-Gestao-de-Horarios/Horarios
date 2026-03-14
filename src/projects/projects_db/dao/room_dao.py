from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.room import Room


class RoomDAO(BaseDAO[Room]):
    def __init__(self, session: Session) -> None:
        super().__init__(Room, session)

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
        return self._create(name=name, type=type, size=size, seats=seats)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_name(self, name: str) -> Room | None:
        return self.session.scalars(select(Room).where(Room.name == name)).first()
