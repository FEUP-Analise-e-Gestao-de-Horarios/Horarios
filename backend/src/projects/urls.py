from django.urls import include, path

from src.projects.views.classes import ProjectClassesView, ProjectClassView
from src.projects.views.degrees import ProjectDegreesView, ProjectDegreeView
from src.projects.views.parallel_blocks import (
    ProjectParallelBlockCandidateView,
    ProjectParallelBlockGroupsView,
)
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

parallel_block_patterns = [
    path("candidates", ProjectParallelBlockCandidateView.as_view()),
    path("groups/", ProjectParallelBlockGroupsView.as_view()),
]

project_patterns = [
    path("stats", ProjectStatsView.as_view()),
    path("rooms/", include(room_patterns)),
    path("teachers/", include(teacher_patterns)),
    path("degrees/", include(degree_patterns)),
    path("years/", include(year_patterns)),
    path("subjects/", include(subject_patterns)),
    path("classes/", include(class_patterns)),
    path("sessions/", include(session_patterns)),
    path("parallel-blocks/", include(parallel_block_patterns)),
]

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>", ProjectView.as_view()),
    path("<int:project_id>/", include(project_patterns)),
]
