from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.year import YearStats


class YearDAO(BaseDAO[Year]):
    """Data access object for Year records."""

    def __init__(self, session: Session, *, flush_on_create: bool = True) -> None:
        super().__init__(Year, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, degree_id: UUID, number: int) -> Year:
        """Create and persist a new year.

        Args:
            degree_id: UUID of the degree this year belongs to.
            number: The year number within the degree (e.g. 1, 2, 3).

        Returns:
            The newly created Year instance, flushed to the session.
        """
        return self._create(degree_id=degree_id, number=number)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[YearStats]:
        """Return all years with their subject, class, and session counts.

        Returns:
            A list of YearStats, one per year, in an unspecified order.
        """
        return self._get_with_stats()

    def get_by_degree_with_stats(self, degree_id: UUID) -> list[YearStats]:
        """Return all years for a degree with their subject, class, and session counts.

        Args:
            degree_id: UUID of the degree to filter years by.

        Returns:
            A list of YearStats, one per year in the given degree.
        """
        return self._get_with_stats(degree_id=degree_id)

    def _get_with_stats(self, *, degree_id: UUID | None = None) -> list[YearStats]:
        subjects_sq = (
            select(Subject.year_id, func.count(Subject.id).label("cnt"))
            .group_by(Subject.year_id)
            .subquery()
        )
        classes_sq = (
            select(Class.year_id, func.count(Class.id).label("cnt"))
            .group_by(Class.year_id)
            .subquery()
        )
        sessions_sq = (
            select(Subject.year_id, func.count(distinct(SessionModel.id)).label("cnt"))
            .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
            .join(SessionModel, SessionModel.id == SessionClassSubject.session_id)
            .group_by(Subject.year_id)
            .subquery()
        )

        stmt = (
            select(
                Year.id,
                Year.number,
                Year.degree_id,
                Degree.acronym.label("degree_acronym"),
                Degree.name.label("degree_name"),
                func.coalesce(subjects_sq.c.cnt, 0).label("subjects"),
                func.coalesce(classes_sq.c.cnt, 0).label("classes"),
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
            )
            .join(Degree, Degree.id == Year.degree_id)
            .outerjoin(subjects_sq, subjects_sq.c.year_id == Year.id)
            .outerjoin(classes_sq, classes_sq.c.year_id == Year.id)
            .outerjoin(sessions_sq, sessions_sq.c.year_id == Year.id)
        )
        if degree_id is not None:
            stmt = stmt.where(Year.degree_id == degree_id)

        rows = self.session.execute(stmt).all()

        return [YearStats.model_validate(row, from_attributes=True) for row in rows]
