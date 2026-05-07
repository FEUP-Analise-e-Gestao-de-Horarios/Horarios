from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.projects.projects_db.base import Base


class BaseDAO[T: Base]:
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
