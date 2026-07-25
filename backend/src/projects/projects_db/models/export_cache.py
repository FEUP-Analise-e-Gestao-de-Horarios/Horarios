from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ExportCache(Base):
    """Cached exporter payloads for a project database."""

    __tablename__ = "export_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def __str__(self) -> str:
        return f"ExportCache(cache_key={self.cache_key!r})"

    __repr__ = __str__
