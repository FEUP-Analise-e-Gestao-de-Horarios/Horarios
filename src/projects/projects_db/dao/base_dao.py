from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from src.projects.projects_db.base import Base

T = TypeVar("T", bound=Base)



class BaseDAO[T]:
    def __init__(self, model: type[T], session: Session) -> None:
        self.model = model
        self.session = session

    def get(self, id: UUID) -> T | None:
        return self.session.get(self.model, id)

    def get_all(self) -> list[T]:
        return self.session.query(self.model).all()

    def _create(self, **kwargs: Any) -> T:
        instance = self.model(**kwargs)
        self.session.add(instance)

        # Write to DB within transaction; validate constraints early
        self.session.flush()
        return instance

    def delete(self, instance: T) -> None:
        self.session.delete(instance)

    def delete_by_id(self, id: UUID) -> bool:
        instance = self.get(id)
        if instance is None:
            return False

        self.session.delete(instance)
        return True
