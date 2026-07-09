import json
from collections.abc import Mapping
from typing import cast

from pydantic import BaseModel
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from src.exporter.schemas import ExportJsonValue
from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.export_cache import ExportCache


class ExportCacheDAO(BaseDAO[ExportCache]):
    """Data access object for cached exporter response payloads."""

    PROJECT_EXPORT_KEY = "project_export"
    PROJECT_EXPORT_VERSION_KEY = "project_export_version"
    SESSION_VERSION_KEY = "project_export_session_version"

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(ExportCache, session, flush_on_create=flush_on_create)
        self.ensure_cache_table()
        self.ensure_session_version_tracking()

    def ensure_cache_table(self) -> None:
        """Create the cache table for project DBs created before this model existed."""
        ExportCache.__table__.create(bind=self.session.get_bind(), checkfirst=True)

    def ensure_session_version_tracking(self) -> None:
        """Create cheap invalidation triggers for schedule tables."""
        if self.session.get(ExportCache, self.SESSION_VERSION_KEY) is None:
            self.session.add(
                ExportCache(
                    cache_key=self.SESSION_VERSION_KEY,
                    payload="0",
                ),
            )
            self.session.flush()

        for table_name in (
            "sessions",
            "session_rooms",
            "session_teachers",
            "sessions_classes_subject",
        ):
            for action in ("INSERT", "UPDATE", "DELETE"):
                trigger_name = f"export_cache_version_{table_name}_{action.lower()}"
                trigger_exists = self.session.scalar(
                    text(
                        "SELECT 1 FROM sqlite_master "
                        "WHERE type = 'trigger' AND name = :trigger_name",
                    ),
                    {"trigger_name": trigger_name},
                )
                if trigger_exists:
                    continue
                self.session.execute(
                    text(
                        f"""
                        CREATE TRIGGER IF NOT EXISTS {trigger_name}
                        AFTER {action} ON {table_name}
                        BEGIN
                            UPDATE export_cache
                            SET
                                payload = CAST(CAST(payload AS INTEGER) + 1 AS TEXT),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE cache_key = '{self.SESSION_VERSION_KEY}';
                        END
                        """,
                    ),
                )

    def get_project_export_payload(
        self,
        version: str | None = None,
    ) -> dict[str, ExportJsonValue] | None:
        if version is not None and self.get_project_export_version() != version:
            return None

        cached = self.session.get(ExportCache, self.PROJECT_EXPORT_KEY)
        if cached is None:
            return None

        payload = json.loads(cached.payload)
        return cast(dict[str, ExportJsonValue], payload) if isinstance(payload, dict) else None

    def get_project_export_version(self) -> str | None:
        cached = self.session.get(ExportCache, self.PROJECT_EXPORT_VERSION_KEY)
        return cached.payload if cached is not None else None

    def get_current_session_version(self) -> str:
        cached = self.session.get(ExportCache, self.SESSION_VERSION_KEY)
        if cached is None:
            return "0"
        return cached.payload

    def has_project_export_payload(self) -> bool:
        return self.session.get(ExportCache, self.PROJECT_EXPORT_KEY) is not None

    def replace_project_export_payload(
        self,
        payload: BaseModel | Mapping[str, ExportJsonValue],
        version: str | None = None,
    ) -> None:
        payload_data = (
            payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        )
        self.session.merge(
            ExportCache(
                cache_key=self.PROJECT_EXPORT_KEY,
                payload=json.dumps(payload_data, default=str),
            ),
        )
        if version is not None:
            self.session.merge(
                ExportCache(
                    cache_key=self.PROJECT_EXPORT_VERSION_KEY,
                    payload=version,
                ),
            )
        self.session.flush()

    def clear_project_export_payload(self) -> None:
        self.session.execute(
            delete(ExportCache).where(
                ExportCache.cache_key.in_(
                    [self.PROJECT_EXPORT_KEY, self.PROJECT_EXPORT_VERSION_KEY],
                ),
            ),
        )
        self.session.flush()
