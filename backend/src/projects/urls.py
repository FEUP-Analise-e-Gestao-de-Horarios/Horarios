from django.urls import include, path

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
from src.projects.views.sessions import ProjectSessionsView
from src.projects.views.stats import ProjectStatsView
from src.projects.views.subjects import ProjectSubjectsView, ProjectSubjectView
from src.projects.views.teachers import ProjectTeachersView, ProjectTeacherView
from src.projects.views.years import ProjectYearsView, ProjectYearView

app_name = "projects"

room_patterns = [
    path("", ProjectRoomsView.as_view()),
    path("<uuid:room_id>", ProjectRoomView.as_view()),
]

teacher_patterns = [
    path("", ProjectTeachersView.as_view()),
    path("<uuid:teacher_id>", ProjectTeacherView.as_view()),
]

degree_patterns = [
    path("", ProjectDegreesView.as_view()),
    path("<uuid:degree_id>", ProjectDegreeView.as_view()),
    path("with-parallel-candidates/", ProjectDegreesWithParallelCandidatesView.as_view()),
]

year_patterns = [
    path("", ProjectYearsView.as_view()),
    path("<uuid:year_id>", ProjectYearView.as_view()),
]

subject_patterns = [
    path("", ProjectSubjectsView.as_view()),
    path("<uuid:subject_id>", ProjectSubjectView.as_view()),
]

class_patterns = [
    path("", ProjectClassesView.as_view()),
    path("<uuid:class_id>", ProjectClassView.as_view()),
]

session_patterns = [
    path("", ProjectSessionsView.as_view()),
]

project_patterns = [
    path("", ProjectView.as_view()),
    path("/stats", ProjectStatsView.as_view()),
    path("/rooms/", include(room_patterns)),
    path("/teachers/", include(teacher_patterns)),
    path("/degrees/", include(degree_patterns)),
    path("/parallel-candidates", ProjectParallelBlockCandidateView.as_view()),
    path("/parallel-groups", ProjectParallelBlockGroupMembersView.as_view()),
    path("/years/", include(year_patterns)),
    path("/subjects/", include(subject_patterns)),
    path("/classes/", include(class_patterns)),
    path("/sessions/", include(session_patterns)),
]

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>", include(project_patterns)),
]
