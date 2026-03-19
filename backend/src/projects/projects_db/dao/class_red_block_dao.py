from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.class_red_block import ClassRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay


class ClassRedBlockDAO(BaseDAO[ClassRedBlock]):
    def __init__(self, session: Session) -> None:
        super().__init__(ClassRedBlock, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, class_id: UUID, hour: int, weekday: WeekDay) -> ClassRedBlock:
        return self._create(class_id=class_id, hour=hour, weekday=weekday)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_class(self, class_id: UUID) -> list[ClassRedBlock]:
        return list(
            self.session.scalars(
                select(ClassRedBlock).where(ClassRedBlock.class_id == class_id),
            ).all(),
        )
