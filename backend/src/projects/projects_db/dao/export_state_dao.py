from sqlalchemy import text
from sqlalchemy.orm import Session


class ExportStateDAO:
    """Data access for exporter invalidation state in a project database."""

    DIRTY_KEY = "project_export_dirty"

    def __init__(self, session: Session) -> None:
        self.session = session

    def is_project_export_dirty(self) -> bool:
        value = self.session.scalar(
            text("SELECT value FROM export_state WHERE key = :dirty_key"),
            {"dirty_key": self.DIRTY_KEY},
        )
        return value != "0"

    def mark_project_export_clean(self) -> None:
        self.session.execute(
            text(
                """
                INSERT INTO export_state (key, value, updated_at)
                VALUES (:dirty_key, '0', CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = '0',
                    updated_at = CURRENT_TIMESTAMP
                """,
            ),
            {"dirty_key": self.DIRTY_KEY},
        )
        self.session.flush()
