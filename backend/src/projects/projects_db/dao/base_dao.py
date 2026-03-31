from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from src.projects.projects_db.base import Base

T = TypeVar("T", bound=Base)


class BaseDAO[T]:
    """Generic base DAO providing CRUD operations for a single SQLAlchemy model."""

    def __init__(self, model: type[T], session: Session, *, flush_on_create: bool = True) -> None:
        """Initialize the DAO with a model class and database session.

        Args:
            model: The SQLAlchemy model class this DAO manages.
            session: The SQLAlchemy session used for database operations.
            flush_on_create: If True, flush the session after each create call.
        """
        self.model = model
        self.session = session
        self.flush_on_create = flush_on_create

    def get(self, id: UUID) -> T | None:
        """Retrieve a single record by its primary key.

        Args:
            id: The UUID primary key of the record.

        Returns:
            The matching model instance, or None if not found.
        """
        return self.session.get(self.model, id)

    def get_all(self) -> list[T]:
        """Retrieve all records of this model.

        Returns:
            A list of all model instances, in an unspecified order.
        """
        return self.session.query(self.model).all()

    def _create(self, **kwargs: Any) -> T:
        """Create a new record and flush it to the session.

        Args:
            **kwargs: Column values forwarded to the model constructor.

        Returns:
            The newly created model instance, flushed to the session.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)

        if self.flush_on_create:
            self.session.flush()
        return instance

    def delete(self, instance: T) -> None:
        """Mark a model instance for deletion from the database.

        Args:
            instance: The model instance to delete.
        """
        self.session.delete(instance)

    def delete_by_id(self, id: UUID) -> bool:
        """Delete a record by its primary key.

        Args:
            id: The UUID primary key of the record to delete.

        Returns:
            True if the record was found and deleted, False if not found.
        """
        instance = self.get(id)
        if instance is None:
            return False

        self.session.delete(instance)
        return True

    def get_added_removed_records(
        self,
        other_db_path: str | Path,
    ) -> dict[str, list[dict[Any, Any]]]:
        table_name = self.model.__tablename__

        conn = self.session.connection()
        try:
            conn.execute(text(f"ATTACH DATABASE '{other_db_path}' AS other_db"))

            added_query = text(
                f"""
            SELECT * FROM main.{table_name}
            EXCEPT
            SELECT * FROM other.{table_name}
            """,
            )

            removed_query = text(
                f"""
                SELECT * FROM other.{table_name}
                EXCEPT
                SELECT * FROM main.{table_name}
            """,
            )

            added = conn.execute(added_query).mappings().all()
            removed = conn.execute(removed_query).mappings().all()

            return {
                "added": [dict(r) for r in added],
                "removed": [dict(r) for r in removed],
            }

        finally:
            conn.execute(text("DETACH DATABASE other_db"))

    def get_changes_only(self, other_db_path: str | Path) -> dict[str, dict[str, dict[str, Any]]]:
        mapper = inspect(self.model)
        table_name = self.model.__tablename__
        pk_name = mapper.primary_key[0].name
        columns = [c.key for c in mapper.attrs if hasattr(c, "columns") and c.key != pk_name]

        conn = self.session.connection()
        try:
            conn.execute(text(f"ATTACH DATABASE '{other_db_path}' AS other_db"))

            # We select BOTH versions of the data to compare them in Python
            # We suffix them with _new and _old
            select_cols = ", ".join(
                [f'main."{c}" AS "{c}_new", other."{c}" AS "{c}_old"' for c in columns],
            )

            query = text(
                f"""
                SELECT main."{pk_name}", {select_cols}
                FROM {table_name} AS main
                INNER JOIN other_db.{table_name} AS other ON main."{pk_name}" = other."{pk_name}"
                WHERE {" OR ".join([f'main."{c}" IS NOT other."{c}"' for c in columns])}
            """,
            )

            results = conn.execute(query).mappings().all()

            diffs = {}
            for row in results:
                pk_val = row[pk_name]
                # Create a dict of ONLY the fields that are different
                changes = {
                    col: {"from": row[f"{col}_old"], "to": row[f"{col}_new"]}
                    for col in columns
                    if row[f"{col}_old"] != row[f"{col}_new"]
                }
                diffs[pk_val] = changes

            return diffs

        finally:
            conn.execute(text("DETACH DATABASE other_db"))
