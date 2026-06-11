"""DAO for reading and tagging persisted conflict groups."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from src.projects.projects_db.dao.tag_dao import TagDAO
from src.projects.projects_db.models.conflict import Conflict


class ConflictDAO:
    """Read and tag conflict groups."""

    def __init__(self, session: DBSession) -> None:
        self.session = session
        self._tags = TagDAO(session)

    def get_tag_assignments(self) -> dict[str, str]:
        """Return a mapping of conflict_id → tag name for all stored conflicts."""
        conflicts = self.session.scalars(
            select(Conflict).options(selectinload(Conflict.tag)),
        ).all()
        return {str(c.conflict_id): c.tag.name for c in conflicts}

    def create_many(self, rows: list[dict]) -> None:
        self.session.execute(insert(Conflict), rows)

    def create_many_tagged(self, rows: list[dict], tag_name: str) -> None:
        tag = self._tags.get_or_create(tag_name)
        tagged = [{**row, "tag_id": tag.tag_id} for row in rows]
        self.session.execute(insert(Conflict), tagged)

    def delete_all(self) -> None:
        self.session.execute(delete(Conflict))

    def update_tag(self, conflict_id: UUID, tag: str | None) -> None:
        """Assign or clear a tag on a conflict.

        Passing None removes the conflict from storage (clears its tag).
        """
        if tag is None:
            self.session.execute(
                delete(Conflict).where(Conflict.conflict_id == conflict_id),
            )
            self.session.commit()
            return

        tag_obj = self._tags.get_or_create(tag)
        existing = self.session.scalars(
            select(Conflict).where(Conflict.conflict_id == conflict_id),
        ).first()
        if existing is not None:
            self.session.execute(
                update(Conflict)
                .where(Conflict.conflict_id == conflict_id)
                .values(tag_id=tag_obj.tag_id),
            )
        else:
            self.session.add(Conflict(conflict_id=conflict_id, tag_id=tag_obj.tag_id))
        self.session.commit()
