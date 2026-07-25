from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from src.projects.projects_db.migrations import export_dirty_triggers

PROJECT_DB_MIGRATIONS_TABLE = "project_db_migrations"
PROJECT_DB_MIGRATIONS: tuple[tuple[str, Callable[[Connection], None]], ...] = (
    ("0001_export_dirty_triggers", export_dirty_triggers.apply),
)


def run_project_db_migrations(engine: Engine) -> None:
    """Apply idempotent migrations to one per-project SQLite database."""
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {PROJECT_DB_MIGRATIONS_TABLE} (
                    migration_id TEXT PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """,
            ),
        )
        applied = set(
            connection.execute(
                text(f"SELECT migration_id FROM {PROJECT_DB_MIGRATIONS_TABLE}"),
            ).scalars(),
        )

        for migration_id, migration in PROJECT_DB_MIGRATIONS:
            if migration_id in applied:
                continue
            migration(connection)
            connection.execute(
                text(
                    f"""
                    INSERT INTO {PROJECT_DB_MIGRATIONS_TABLE} (migration_id)
                    VALUES (:migration_id)
                    """,
                ),
                {"migration_id": migration_id},
            )
