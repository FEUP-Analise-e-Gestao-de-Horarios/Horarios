from src.projects.views.classes import ProjectClassesView, ProjectClassView
from src.projects.views.degrees import (
    ProjectDegreesView,
    ProjectDegreesWithParallelCandidatesView,
    ProjectDegreeView,
)
from src.projects.views.parallel_block_candidates import ProjectParallelBlockCandidateView
from src.projects.views.parallel_block_group_members import ProjectParallelBlockGroupMembersView
from src.projects.views.project import ProjectsView, ProjectView
from src.projects.views.rooms import ProjectRoomsView, ProjectRoomView
from src.projects.views.stats import ProjectStatsView
from src.projects.views.subjects import ProjectSubjectsView, ProjectSubjectView
from src.projects.views.teachers import ProjectTeachersView, ProjectTeacherView
from src.projects.views.years import ProjectYearsView

__all__ = [
    "ProjectClassView",
    "ProjectClassesView",
    "ProjectDegreeView",
    "ProjectDegreesView",
    "ProjectDegreesWithParallelCandidatesView",
    "ProjectParallelBlockCandidateView",
    "ProjectParallelBlockGroupMembersView",
    "ProjectRoomView",
    "ProjectRoomsView",
    "ProjectStatsView",
    "ProjectSubjectView",
    "ProjectSubjectsView",
    "ProjectTeacherView",
    "ProjectTeachersView",
    "ProjectView",
    "ProjectYearsView",
    "ProjectsView",
]
