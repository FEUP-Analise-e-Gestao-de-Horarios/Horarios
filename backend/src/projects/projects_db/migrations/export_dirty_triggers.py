from sqlalchemy import Connection, text

EXPORT_DIRTY_KEY = "project_export_dirty"
EXPORTER_DIRTY_TABLES = (
    "sessions",
    "session_rooms",
    "session_teachers",
    "sessions_classes_subject",
    "rooms",
    "teachers",
    "classes",
    "subjects",
)
TRIGGER_ACTIONS = ("INSERT", "UPDATE", "DELETE")


def apply(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS export_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ),
    )
    connection.execute(
        text(
            """
            INSERT OR IGNORE INTO export_state (key, value)
            VALUES (:dirty_key, '1')
            """,
        ),
        {"dirty_key": EXPORT_DIRTY_KEY},
    )

    _drop_old_version_counter_triggers(connection)
    _clear_old_version_counter_cache_rows(connection)

    for table_name in EXPORTER_DIRTY_TABLES:
        for action in TRIGGER_ACTIONS:
            trigger_name = f"export_dirty_{table_name}_{action.lower()}"
            connection.execute(
                text(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {trigger_name}
                    AFTER {action} ON {table_name}
                    BEGIN
                        INSERT OR IGNORE INTO export_state (key, value, updated_at)
                        VALUES ('{EXPORT_DIRTY_KEY}', '1', CURRENT_TIMESTAMP);
                        UPDATE export_state
                        SET value = '1',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE key = '{EXPORT_DIRTY_KEY}';
                    END
                    """,
                ),
            )


def _drop_old_version_counter_triggers(connection: Connection) -> None:
    for table_name in (
        "sessions",
        "session_rooms",
        "session_teachers",
        "sessions_classes_subject",
    ):
        for action in TRIGGER_ACTIONS:
            trigger_name = f"export_cache_version_{table_name}_{action.lower()}"
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))


def _clear_old_version_counter_cache_rows(connection: Connection) -> None:
    connection.execute(
        text(
            """
            DELETE FROM export_cache
            WHERE cache_key IN (
                'project_export_version',
                'project_export_session_version'
            )
            """,
        ),
    )
