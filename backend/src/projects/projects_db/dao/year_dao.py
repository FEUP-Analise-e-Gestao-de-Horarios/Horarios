from uuid import UUID

from backend.src.projects.projects_db.dao.utils import parallel_sessions_subquery
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
    def __init__(self, session: Session) -> None:
        super().__init__(Year, session)

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

    def get_by_degree_and_number(self, *, degree_acronym: str, number: int) -> Year | None:
        """Retrieve a year by its degree acronym and year number.

        Args:
            degree_acronym: The acronym of the parent degree.
            number: The year number within the degree.

        Returns:
            The matching Year instance, or None if not found.
        """
        return self.session.scalars(
            select(Year)
            .join(Year.degree)
            .where(Degree.acronym == degree_acronym, Year.number == number),
        ).first()

    def get_by_degree_with_stats(self, degree_id: UUID) -> list[YearStats]:
        """Return all years for a degree with their subject, class, and session counts.

        Args:
            degree_id: UUID of the degree to filter years by.

        Returns:
            A list of YearStats, one per year in the given degree.
        """
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

        rows = self.session.execute(
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
            .where(Year.degree_id == degree_id),
        ).all()

        return [YearStats.model_validate(row, from_attributes=True) for row in rows]

    def get_with_parallel_classes(self, degree_id: UUID) -> list[Year]:
        parallel = parallel_sessions_subquery()
        return list(
            self.session.scalars(
                select(Year)
                .join(Subject, Subject.year_id == Year.id)
                .join(parallel, parallel.c.subject_id == Subject.id)
                .where(Year.degree_id == degree_id)
                .distinct(),
            ).all(),
        )
