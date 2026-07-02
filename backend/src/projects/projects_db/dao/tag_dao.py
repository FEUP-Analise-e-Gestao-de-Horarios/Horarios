from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.models.tag import Tag


class TagDAO:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    def get_all(self) -> list[str]:
        return [t.name for t in self.session.scalars(select(Tag)).all()]

    def get_or_create(self, name: str) -> Tag:
        tag = self.session.scalars(select(Tag).where(Tag.name == name)).first()
        if tag is None:
            tag = Tag(tag_id=uuid.uuid4(), name=name)
            self.session.add(tag)
            self.session.flush()
        return tag
