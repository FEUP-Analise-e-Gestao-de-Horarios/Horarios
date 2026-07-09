from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ExportChecklistItem(Base):
    """Persisted checklist state for exporter work items."""

    __tablename__ = "export_checklist_items"

    item_key: Mapped[str] = mapped_column(Text, primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def __str__(self) -> str:
        return f"ExportChecklistItem(item_key={self.item_key!r})"

    __repr__ = __str__
