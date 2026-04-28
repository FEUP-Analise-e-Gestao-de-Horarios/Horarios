import random
import re
import string
from collections.abc import Hashable, Sequence
from pathlib import Path
from typing import Any, TypedDict, TypeVar
from uuid import UUID

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from src.projects.projects_db.base import Base

T = TypeVar("T", bound=Base)

type DBAlias = str
"""SQLite schema alias assigned to a database attached on the current connection.

A ``DBAlias`` is the symbolic name used in SQLite statements such as
``ATTACH DATABASE ... AS <alias>``. Once attached, the alias qualifies tables
in cross-database comparisons, for example ``other_alias.some_table``.

Aliases created by :meth:`BaseDAO.attach_db` are random 8-character lowercase
ASCII identifiers and are safe to pass to
:meth:`BaseDAO.get_added_removed_records`, :meth:`BaseDAO.get_changes_only`,
and :meth:`BaseDAO.detach_db`.
"""


type DBRecordKey = Hashable
"""Hashable primary-key value that identifies a single database record.

For tables with a single-column primary key, this is that scalar value.
For composite primary keys, this is a tuple ordered exactly like the model's
declared primary-key columns.
"""


type DBRecord = dict[str, Any]
"""A database row serialized as a plain ``dict`` keyed by column name."""


class AddedRemovedRecords(TypedDict):
    """Rows present only in the current database or only in an attached one.

    Attributes:
        added: Rows that exist in the current ``main`` database but not in the
            attached database.
        removed: Rows that exist in the attached database but not in the current
            ``main`` database.
    """

    added: list[DBRecord]
    removed: list[DBRecord]


class ColumnChange(TypedDict):
    """Before-and-after values for one changed column on a matched record.

    Attributes:
        old: Value stored in the attached database.
        new: Value stored in the current ``main`` database.
    """

    old: Any
    new: Any


type RecordChanges = dict[str, ColumnChange | AddedRemovedRecords]
"""Changed columns for a single record, keyed by column name."""


type ChangedRecords = dict[DBRecordKey, RecordChanges]
"""Field-level changes for records present in both compared databases.

Structure::

    ChangedRecords[primary_key][column_name] = {"old": old_value, "new": new_value}
"""


_SQLITE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BaseDAO[T]:
    """Generic base DAO providing CRUD operations for a single SQLAlchemy model."""

    def __init__(
        self,
        model: type[T],
        session: Session,
        *,
        flush_on_create: bool = True,
    ) -> None:
        """Initialize the DAO with a model class and database session.

        Args:
            model: The SQLAlchemy model class this DAO manages.
            session: The SQLAlchemy session used for database operations.
            flush_on_create: If True, flush the session after each create call.
        """
        self.model = model
        self.session = session
        self.flush_on_create = flush_on_create

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _validate_db_alias(alias: str) -> DBAlias:
        if not _SQLITE_IDENTIFIER_RE.fullmatch(alias):
            raise ValueError(
                "Database aliases must be valid SQLite identifiers "
                "(letters, digits, and underscores; cannot start with a digit).",
            )
        return alias

    def _qualified_table_name(self, db_alias: str, table_name: str) -> str:
        return f"{self._quote_identifier(db_alias)}.{self._quote_identifier(table_name)}"

    def get(self, primary_key: DBRecordKey) -> T | None:
        """Retrieve a single record by its primary key.

        Args:
            primary_key: Scalar or composite primary-key value of the record.

        Returns:
            The matching model instance, or None if not found.
        """
        return self.session.get(self.model, primary_key)

    def get_all(self) -> list[T]:
        """Retrieve all records of this model.

        Returns:
            A list of all model instances, in an unspecified order.
        """
        return self.session.query(self.model).all()

    def get_multiple(self, primary_keys: Sequence[DBRecordKey]) -> list[T]:
        pk_cols = inspect(self.model).primary_key

        primary_keys = [UUID(hex=i) if isinstance(i, str) else i for i in primary_keys]

        if len(pk_cols) != 1:
            raise ValueError("get_multiple only supports single-column primary keys")

        stmt = select(self.model).where(pk_cols[0].in_(primary_keys))
        return list(self.session.scalars(stmt).all())

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

    def delete_by_id(self, primary_key: DBRecordKey) -> bool:
        """Delete a record by its primary key.

        Args:
            primary_key: Scalar or composite primary-key value of the record to
                delete.

        Returns:
            True if the record was found and deleted, False if not found.
        """
        instance = self.get(primary_key)
        if instance is None:
            return False

        self.session.delete(instance)
        return True

    def get_added_removed_records(
        self,
        other_db_alias: DBAlias,
        pk_list: list[str],
        table_name: str,
    ) -> AddedRemovedRecords:
        """Return rows that exist only in the current or only in an attached database.

        The comparison is performed against the same table in another SQLite
        database attached to the current connection.

        Args:
            other_db_alias: Alias previously returned by :meth:`attach_db`.

        Returns:
            A mapping with two lists of plain row dictionaries:
            ``added`` contains rows present in ``main`` but not in the attached
            database, and ``removed`` contains rows present in the attached
            database but not in ``main``.
        """
        other_alias = self._validate_db_alias(other_db_alias)
        current_table = self._qualified_table_name("main", table_name)
        other_table = self._qualified_table_name(other_alias, table_name)

        conn = self.session.connection()

        added_query = text(
            f"""
        SELECT {",".join(pk_list)} FROM {current_table}
        EXCEPT
        SELECT {",".join(pk_list)} FROM {other_table}
        """,
        )

        removed_query = text(
            f"""
            SELECT {",".join(pk_list)} FROM {other_table}
            EXCEPT
            SELECT {",".join(pk_list)} FROM {current_table}
        """,
        )

        added = [dict(row) for row in conn.execute(added_query).mappings().all()]
        removed = [dict(row) for row in conn.execute(removed_query).mappings().all()]

        return {
            "added": added,
            "removed": removed,
        }

    def get_changes_only(self, other_db_alias: DBAlias) -> ChangedRecords:
        """Return field-level diffs for records present in both compared databases.

        Records are matched by primary key. If a row exists in only one
        database, it is excluded from this result and should be obtained from
        :meth:`get_added_removed_records` instead. If a primary-key value itself
        changes, SQLite will surface that as one removed row and one added row.

        Args:
            other_db_alias: Alias previously returned by :meth:`attach_db`.

        Returns:
            A mapping keyed by primary-key value. Each value contains only the
            columns whose values differ, with ``old`` coming from the attached
            database and ``new`` coming from the current ``main`` database.
        """
        other_alias = self._validate_db_alias(other_db_alias)
        mapper = inspect(self.model)
        pk_names = [column.name for column in mapper.primary_key]
        columns = [attr.key for attr in mapper.column_attrs if attr.key not in pk_names]
        table_name = self.model.__tablename__

        if not columns:
            return {}

        conn = self.session.connection()

        current_alias = "current_row"
        other_row_alias = "other_row"
        current_table = self._qualified_table_name("main", table_name)
        other_table = self._qualified_table_name(other_alias, table_name)

        select_pk_cols = ", ".join(
            [
                f"{current_alias}.{self._quote_identifier(pk_name)} "
                f"AS {self._quote_identifier(pk_name)}"
                for pk_name in pk_names
            ],
        )
        select_cols = ", ".join(
            [
                f"{current_alias}.{self._quote_identifier(column)} "
                f"AS {self._quote_identifier(f'{column}_new')}, "
                f"{other_row_alias}.{self._quote_identifier(column)} "
                f"AS {self._quote_identifier(f'{column}_old')}"
                for column in columns
            ],
        )
        join_clause = " AND ".join(
            [
                f"{current_alias}.{self._quote_identifier(pk_name)} = "
                f"{other_row_alias}.{self._quote_identifier(pk_name)}"
                for pk_name in pk_names
            ],
        )
        where_clause = " OR ".join(
            [
                f"{current_alias}.{self._quote_identifier(column)} IS NOT "
                f"{other_row_alias}.{self._quote_identifier(column)}"
                for column in columns
            ],
        )

        query = text(
            f"""
            SELECT {select_pk_cols}, {select_cols}
            FROM {current_table} AS {current_alias}
            INNER JOIN {other_table} AS {other_row_alias}
                ON {join_clause}
            WHERE {where_clause}
        """,
        )

        results = conn.execute(query).mappings().all()

        diffs: ChangedRecords = {}
        for row in results:
            pk_value: DBRecordKey
            if len(pk_names) == 1:
                pk_value = row[pk_names[0]]
            else:
                pk_value = tuple(row[pk_name] for pk_name in pk_names)

            changes = {
                column: {
                    "old": row[f"{column}_old"],
                    "new": row[f"{column}_new"],
                }
                for column in columns
                if row[f"{column}_old"] != row[f"{column}_new"]
            }
            diffs[pk_value] = changes

        return diffs

    def attach_db(self, other_db_path: str | Path) -> DBAlias:
        """Attach another SQLite database to the current connection.

        Args:
            other_db_path: Filesystem path to the SQLite database file to
                attach.

        Returns:
            The generated alias that SQLite assigned for qualifying tables from
            the attached database in future calls.
        """
        alias: DBAlias = "".join(random.choices(string.ascii_lowercase, k=8))

        conn = self.session.connection()
        conn.execute(
            text(f"ATTACH DATABASE :db_path AS {self._quote_identifier(alias)}"),
            {"db_path": str(other_db_path)},
        )

        return alias

    def detach_db(self, alias: DBAlias) -> None:
        """Detach a previously attached SQLite database from the current connection.

        Args:
            alias: Alias previously returned by :meth:`attach_db`.
        """
        validated_alias = self._validate_db_alias(alias)
        conn = self.session.connection()
        conn.execute(text(f"DETACH DATABASE {self._quote_identifier(validated_alias)}"))
