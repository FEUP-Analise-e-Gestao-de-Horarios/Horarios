from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.exceptions import MultipleNotFoundError
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
    
    def get_by_names(self, names: set[str], *, check_count: bool = True) -> list[Room]:
        if not names:
            return []

        rooms = list(self.session.scalars(select(Room).where(Room.name.in_(names))).all())
        if check_count and len(names) != len(rooms):
            found = {r.name for r in rooms}
            missing = names - found
            raise MultipleNotFoundError("name", missing)

        return rooms
