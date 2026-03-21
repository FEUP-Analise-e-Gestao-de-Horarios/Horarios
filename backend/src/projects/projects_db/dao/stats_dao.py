from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.models.year import Year
from src.projects.projects_db.schemas.stats import ProjectOverviewStats


class StatsDAO:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_overview(self) -> ProjectOverviewStats:
        counts = self.session.execute(
            select(
                select(func.count(Degree.id)).scalar_subquery().label("num_degrees"),
                select(func.count(Year.id)).scalar_subquery().label("num_years"),
                select(func.count(Subject.id)).scalar_subquery().label("num_subjects"),
                select(func.count(Class.id)).scalar_subquery().label("num_classes"),
                select(func.count(Teacher.id)).scalar_subquery().label("num_teachers"),
                select(func.count(Room.id)).scalar_subquery().label("num_rooms"),
                select(func.count(SessionModel.id)).scalar_subquery().label("num_sessions"),
            )
        ).one()

        return ProjectOverviewStats(
            num_degrees=counts.num_degrees,
            num_years=counts.num_years,
            num_subjects=counts.num_subjects,
            num_classes=counts.num_classes,
            num_teachers=counts.num_teachers,
            num_rooms=counts.num_rooms,
            num_sessions=counts.num_sessions,
        )
