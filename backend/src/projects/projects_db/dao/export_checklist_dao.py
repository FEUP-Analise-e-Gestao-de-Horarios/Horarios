from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.export_checklist_item import ExportChecklistItem


class ExportChecklistDAO(BaseDAO[ExportChecklistItem]):
    """Data access for checked exporter work items."""

    def __init__(self, session: Session, flush_on_create: bool = True) -> None:
        super().__init__(ExportChecklistItem, session, flush_on_create=flush_on_create)
        self.ensure_table()

    def ensure_table(self) -> None:
        ExportChecklistItem.__table__.create(bind=self.session.get_bind(), checkfirst=True)

    def get_checked_item_keys(self) -> list[str]:
        return list(
            self.session.scalars(
                select(ExportChecklistItem.item_key).order_by(ExportChecklistItem.item_key),
            ).all(),
        )

    def set_checked(self, item_key: str, checked: bool) -> list[str]:
        if checked:
            self.session.merge(ExportChecklistItem(item_key=item_key))
        else:
            self.session.execute(
                delete(ExportChecklistItem).where(ExportChecklistItem.item_key == item_key),
            )
        self.session.flush()
        return self.get_checked_item_keys()

    def clear_checked_items(self) -> list[str]:
        self.session.execute(delete(ExportChecklistItem))
        self.session.flush()
        return []
