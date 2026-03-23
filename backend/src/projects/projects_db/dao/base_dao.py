from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from src.projects.projects_db.base import Base

T = TypeVar("T", bound=Base)


class BaseDAO[T]:
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
