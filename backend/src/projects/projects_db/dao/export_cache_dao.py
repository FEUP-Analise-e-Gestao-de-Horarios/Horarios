import json
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.export_cache import ExportCache


class ExportCacheDAO(BaseDAO[ExportCache]):
    """Data access object for cached exporter response payloads."""

    PROJECT_EXPORT_KEY = "project_export"

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(ExportCache, session, flush_on_create=flush_on_create)
        self.ensure_cache_table()

    def ensure_cache_table(self) -> None:
        """Create the cache table for project DBs created before this model existed."""
        ExportCache.__table__.create(bind=self.session.get_bind(), checkfirst=True)

    def get_project_export_payload(self) -> dict[str, Any] | None:
        cached = self.session.get(ExportCache, self.PROJECT_EXPORT_KEY)
        if cached is None:
            return None

        payload = json.loads(cached.payload)
        return payload if isinstance(payload, dict) else None

    def replace_project_export_payload(self, payload: dict[str, Any]) -> None:
        self.session.merge(
            ExportCache(
                cache_key=self.PROJECT_EXPORT_KEY,
                payload=json.dumps(payload, default=str),
            ),
        )
        self.session.flush()

    def clear_project_export_payload(self) -> None:
        self.session.execute(
            delete(ExportCache).where(ExportCache.cache_key == self.PROJECT_EXPORT_KEY),
        )
        self.session.flush()
