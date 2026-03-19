from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.teacher_red_block import TeacherRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay


class TeacherRedBlockDAO(BaseDAO[TeacherRedBlock]):
    def __init__(self, session: Session) -> None:
        super().__init__(TeacherRedBlock, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, teacher_id: UUID, hour: int, weekday: WeekDay) -> TeacherRedBlock:
        return self._create(teacher_id=teacher_id, hour=hour, weekday=weekday)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_teacher(self, teacher_id: UUID) -> list[TeacherRedBlock]:
        return list(
            self.session.scalars(
                select(TeacherRedBlock).where(TeacherRedBlock.teacher_id == teacher_id),
            ).all(),
        )
