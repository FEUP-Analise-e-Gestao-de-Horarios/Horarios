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
        """Initialize the stats DAO.

        Args:
            session: The SQLAlchemy session used for database operations.
        """
        self.session = session

    def get_overview(self) -> ProjectOverviewStats:
        """Return a snapshot of total entity counts across the project database.

        Each count is computed as a correlated scalar subquery, so this always
        issues a single SQL statement that returns exactly one row.

        Returns:
            A ProjectOverviewStats instance with counts for degrees, years,
            subjects, classes, teachers, rooms, and sessions.
        """
        counts = self.session.execute(
            select(
                select(func.count(Degree.id)).scalar_subquery().label("degrees"),
                select(func.count(Year.id)).scalar_subquery().label("years"),
                select(func.count(Subject.id)).scalar_subquery().label("subjects"),
                select(func.count(Class.id)).scalar_subquery().label("classes"),
                select(func.count(Teacher.id)).scalar_subquery().label("teachers"),
                select(func.count(Room.id)).scalar_subquery().label("rooms"),
                select(func.count(SessionModel.id)).scalar_subquery().label("sessions"),
            ),
        ).one()

        return ProjectOverviewStats.model_validate(counts, from_attributes=True)
