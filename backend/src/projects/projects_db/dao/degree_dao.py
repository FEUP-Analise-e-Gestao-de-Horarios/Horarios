from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import session_subjects
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.degree import DegreeStats


class DegreeDAO(BaseDAO[Degree]):
    def __init__(self, session: Session) -> None:
        super().__init__(Degree, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, acronym: str, name: str) -> Degree:
        return self._create(acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_by_acronym(self, acronym: str) -> Degree | None:
        return self.session.scalars(select(Degree).where(Degree.acronym == acronym)).first()

    def get_all_with_stats(self) -> list[DegreeStats]:
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
            .join(session_subjects, session_subjects.c.subject_id == Subject.id)
            .join(SessionModel, SessionModel.id == session_subjects.c.session_id)
            .group_by(Year.degree_id)
            .subquery()
        )

        rows = self.session.execute(
            select(
                Degree.id,
                Degree.acronym,
                Degree.name,
                func.coalesce(years_sq.c.cnt, 0).label("num_years"),
                func.coalesce(subjects_sq.c.cnt, 0).label("num_subjects"),
                func.coalesce(classes_sq.c.cnt, 0).label("num_classes"),
                func.coalesce(sessions_sq.c.cnt, 0).label("num_sessions"),
            )
            .outerjoin(years_sq, years_sq.c.degree_id == Degree.id)
            .outerjoin(subjects_sq, subjects_sq.c.degree_id == Degree.id)
            .outerjoin(classes_sq, classes_sq.c.degree_id == Degree.id)
            .outerjoin(sessions_sq, sessions_sq.c.degree_id == Degree.id),
        ).all()

        return [
            DegreeStats(
                id=row.id,
                acronym=row.acronym,
                name=row.name,
                num_years=row.num_years,
                num_subjects=row.num_subjects,
                num_classes=row.num_classes,
                num_sessions=row.num_sessions,
            )
            for row in rows
        ]
