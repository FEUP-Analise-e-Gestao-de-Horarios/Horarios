from __future__ import annotations

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.models.conflict_teacher import ConflictTeacher


class ConflictTeacherDAO:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    def create_many(self, rows: list[dict]) -> None:
        self.session.execute(insert(ConflictTeacher), rows)

    def delete_all(self) -> None:
        self.session.execute(delete(ConflictTeacher))
