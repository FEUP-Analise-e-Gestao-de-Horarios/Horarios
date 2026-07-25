import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.modified_session import ModifiedSession


class ModifiedSessionDAO(BaseDAO[ModifiedSession]):
    """Data access object for cached export modification ordering."""

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(ModifiedSession, session, flush_on_create=flush_on_create)
        self.ensure_cache_columns()

    def ensure_cache_columns(self) -> None:
        """Add cache payload columns for project DBs created before this model changed."""
        columns = {
            row["name"]
            for row in self.session.execute(text("PRAGMA table_info(modified_sessions)")).mappings()
        }

        if "step_key" not in columns:
            self.session.execute(
                text("ALTER TABLE modified_sessions ADD COLUMN step_key TEXT NOT NULL DEFAULT ''"),
            )

        if "step_payload" not in columns:
            self.session.execute(
                text(
                    "ALTER TABLE modified_sessions "
                    "ADD COLUMN step_payload TEXT NOT NULL DEFAULT ''",
                ),
            )

    @staticmethod
    def normalize_id(value: Any) -> str:
        return str(value).replace("-", "")

    @staticmethod
    def to_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(hex=ModifiedSessionDAO.normalize_id(value))

    def get_ordered_modifications(self) -> list[tuple[UUID, str]]:
        """Return cached ``(session_id, step_type)`` entries in export order."""
        rows = self.session.scalars(
            select(ModifiedSession).order_by(ModifiedSession.modification_number),
        ).all()
        return [(row.session_id, row.step_type) for row in rows]

    def get_cached_modification_steps(self) -> list[dict[str, Any]]:
        """Return cached frontend-ready modification steps, de-duplicated by step key."""
        rows = self.session.scalars(
            select(ModifiedSession).order_by(ModifiedSession.modification_number),
        ).all()
        steps = []
        seen_step_keys = set()

        for row in rows:
            if not row.step_payload or row.step_key in seen_step_keys:
                continue

            steps.append(json.loads(row.step_payload))
            seen_step_keys.add(row.step_key)

        return steps

    def get_session_ids(self) -> set[str]:
        """Return normalized cached session ids."""
        return {
            self.normalize_id(session_id)
            for session_id in self.session.scalars(select(ModifiedSession.session_id)).all()
        }

    def matches_sessions(self, session_ids: Sequence[Any]) -> bool:
        """Return whether the cache describes exactly the provided changed sessions."""
        return self.get_session_ids() == {
            self.normalize_id(session_id) for session_id in session_ids
        }

    def replace_ordered_modifications(
        self,
        ordered_modifications: Sequence[tuple[Any, str]],
    ) -> None:
        """Replace the cached export order with freshly computed graph output."""
        self.session.execute(delete(ModifiedSession))

        for modification_number, (session_id, step_type) in enumerate(
            ordered_modifications,
            start=1,
        ):
            self._create(
                modification_number=modification_number,
                session_id=self.to_uuid(session_id),
                step_type=step_type,
                step_key=str(modification_number),
                step_payload="",
            )

        self.session.flush()

    def replace_modification_steps(self, modification_steps: Sequence[dict[str, Any]]) -> None:
        """Replace cached export steps with the already rendered export payload."""
        self.session.execute(delete(ModifiedSession))

        modification_number = 1
        for step_number, step in enumerate(modification_steps, start=1):
            step_payload = json.dumps(step, default=str)
            for session_id in step["session_ids"]:
                self._create(
                    modification_number=modification_number,
                    session_id=self.to_uuid(session_id),
                    step_type=step["type"],
                    step_key=str(step_number),
                    step_payload=step_payload,
                )
                modification_number += 1

        self.session.flush()

    def clear_modification_steps(self) -> None:
        """Remove cached export modification steps."""
        self.session.execute(delete(ModifiedSession))
        self.session.flush()
