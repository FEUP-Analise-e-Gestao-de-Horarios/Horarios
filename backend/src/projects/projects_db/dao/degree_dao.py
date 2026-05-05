from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.degree import DegreeStats


class DegreeDAO(BaseDAO[Degree]):
    """Data access object for Degree records."""

    def __init__(self, session: Session, *, flush_on_create: bool = True) -> None:
        super().__init__(Degree, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, acronym: str, name: str) -> Degree:
        """Create and persist a new degree.

        Args:
            acronym: Short abbreviation for the degree.
            name: Full name of the degree.

        Returns:
            The newly created Degree instance, flushed to the session.
        """
        return self._create(acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[DegreeStats]:
        """Return all degrees with their year, subject, class, and session counts.

        Counts are computed via subqueries and default to 0 when a degree
        has no associated records.

        Returns:
            A list of DegreeStats, one per degree, in an unspecified order.
        """
        years_sq = (
            select(Year.degree_id, func.count(Year.id).label("cnt"))
            .group_by(Year.degree_id)
            .subquery()
        )
        subjects_sq = (
            select(Year.degree_id, func.count(Subject.id).label("cnt"))
            .join(Subject, Subject.year_id == Year.id)
            .group_by(Year.degree_id)
            .subquery()
        )
        classes_sq = (
            select(Year.degree_id, func.count(Class.id).label("cnt"))
            .join(Class, Class.year_id == Year.id)
            .group_by(Year.degree_id)
            .subquery()
        )
        sessions_sq = (
            select(Year.degree_id, func.count(distinct(SessionModel.id)).label("cnt"))
            .join(Subject, Subject.year_id == Year.id)
            .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
            .join(SessionModel, SessionModel.id == SessionClassSubject.session_id)
            .group_by(Year.degree_id)
            .subquery()
        )

        rows = self.session.execute(
            select(
                Degree.id,
                Degree.acronym,
                Degree.name,
                func.coalesce(years_sq.c.cnt, 0).label("years"),
                func.coalesce(subjects_sq.c.cnt, 0).label("subjects"),
                func.coalesce(classes_sq.c.cnt, 0).label("classes"),
                func.coalesce(sessions_sq.c.cnt, 0).label("sessions"),
            )
            .outerjoin(years_sq, years_sq.c.degree_id == Degree.id)
            .outerjoin(subjects_sq, subjects_sq.c.degree_id == Degree.id)
            .outerjoin(classes_sq, classes_sq.c.degree_id == Degree.id)
            .outerjoin(sessions_sq, sessions_sq.c.degree_id == Degree.id),
        ).all()

        return [DegreeStats.model_validate(row, from_attributes=True) for row in rows]
