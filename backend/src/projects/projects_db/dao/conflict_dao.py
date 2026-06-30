"""DAO for reading and tagging persisted conflict groups."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from src.projects.projects_db.dao.tag_dao import TagDAO
from src.projects.projects_db.models._secondary_tables import conflict_tags
from src.projects.projects_db.models.conflict import Conflict
from src.projects.projects_db.models.tag import Tag


class ConflictDAO:
    """Read and tag conflict groups."""

    def __init__(self, session: DBSession) -> None:
        self.session = session
        self._tags = TagDAO(session)

    def get_tag_assignments(self) -> dict[str, list[str]]:
        """Return a mapping of conflict_id → sorted tag names for all stored conflicts."""
        conflicts = self.session.scalars(
            select(Conflict).options(selectinload(Conflict.tags)),
        ).all()
        return {str(c.conflict_id): sorted(t.name for t in c.tags) for c in conflicts}

    def create_many(self, rows: list[dict]) -> None:
        self.session.execute(insert(Conflict), rows)

    def create_many_tagged(self, rows: list[dict], tag_name: str) -> None:
        tag = self._tags.get_or_create(tag_name)
        self.session.execute(insert(Conflict), rows)
        self.session.execute(
            insert(conflict_tags),
            [{"conflict_id": row["conflict_id"], "tag_id": tag.tag_id} for row in rows],
        )

    def delete_all(self) -> None:
        self.session.execute(delete(Conflict))

    def set_tags(self, conflict_id: UUID, tags: list[str]) -> None:
        """Replace the full set of tags on a conflict.

        An empty list removes the conflict from storage entirely (along with
        its tag associations).
        """
        self._apply_tags(conflict_id, tags)
        self.session.commit()

    def set_tags_many(self, updates: list[tuple[UUID, list[str]]]) -> None:
        """Replace the tags on several conflicts in a single commit."""
        for conflict_id, tags in updates:
            self._apply_tags(conflict_id, tags)
        self.session.commit()

    def _apply_tags(self, conflict_id: UUID, tags: list[str]) -> None:
        """Stage a tag replacement for one conflict. An empty list deletes it."""
        conflict = self.session.get(Conflict, conflict_id)

        if not tags:
            if conflict is not None:
                self.session.delete(conflict)
            return

        if conflict is None:
            conflict = Conflict(conflict_id=conflict_id)
            self.session.add(conflict)

        # Deduplicate while preserving the caller's order.
        unique_names = list(dict.fromkeys(tags))
        conflict.tags = [self._tags.get_or_create(name) for name in unique_names]

    def delete_tag(self, tag_name: str) -> None:
        tag = self.session.scalars(select(Tag).where(Tag.name == tag_name)).first()
        if tag is None:
            return

        # Drop this tag's associations, then any conflict left without tags.
        self.session.execute(delete(conflict_tags).where(conflict_tags.c.tag_id == tag.tag_id))
        tagged = select(conflict_tags.c.conflict_id)
        self.session.execute(delete(Conflict).where(Conflict.conflict_id.notin_(tagged)))
        self.session.delete(tag)
        self.session.commit()
