from src.projects.views.classes import (
    ProjectClassesView,
    ProjectClassView,
    ProjectYearClassesView,
)
from src.projects.views.degrees import ProjectDegreesView, ProjectDegreeView
from src.projects.views.project import ProjectsView, ProjectView
from src.projects.views.rooms import ProjectRoomsView, ProjectRoomView
from src.projects.views.stats import ProjectStatsView
from src.projects.views.subjects import (
    ProjectSubjectsView,
    ProjectSubjectView,
    ProjectYearSubjectsView,
)
from src.projects.views.teachers import ProjectTeachersView, ProjectTeacherView
from src.projects.views.years import (
    ProjectDegreeYearsView,
    ProjectYearsView,
    ProjectYearView,
)

__all__ = [
    "ProjectClassView",
    "ProjectClassesView",
    "ProjectDegreeView",
    "ProjectDegreeYearsView",
    "ProjectDegreesView",
    "ProjectRoomView",
    "ProjectRoomsView",
    "ProjectStatsView",
    "ProjectSubjectView",
    "ProjectSubjectsView",
    "ProjectTeacherView",
    "ProjectTeachersView",
    "ProjectView",
    "ProjectYearClassesView",
    "ProjectYearSubjectsView",
    "ProjectYearView",
    "ProjectYearsView",
    "ProjectsView",
]
