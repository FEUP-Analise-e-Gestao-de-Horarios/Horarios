from django.urls import include, path

from src.projects.views import (
    ProjectClassesView,
    ProjectDegreesView,
    ProjectDegreesWithParallelCandidatesView,
    ProjectDegreeView,
    ProjectParallelBlockCandidateView,
    ProjectParallelBlockGroupMembersView,
    ProjectRoomsView,
    ProjectRoomView,
    ProjectStatsView,
    ProjectSubjectsView,
    ProjectsView,
    ProjectTeachersView,
    ProjectTeacherView,
    ProjectView,
    ProjectYearsView,
)

app_name = "projects"

year_patterns = [
    path("", ProjectYearsView.as_view()),
    path("<uuid:year_id>/subjects/", ProjectSubjectsView.as_view()),
    path("<uuid:year_id>/classes/", ProjectClassesView.as_view()),
]

degree_patterns = [
    path("", ProjectDegreesView.as_view()),
    path("with-parallel-candidates/", ProjectDegreesWithParallelCandidatesView.as_view()),
    path("<uuid:degree_id>", ProjectDegreeView.as_view()),
    path("<uuid:degree_id>/years/", include(year_patterns)),
]

teacher_patterns = [
    path("", ProjectTeachersView.as_view()),
    path("<uuid:teacher_id>", ProjectTeacherView.as_view()),
]

room_patterns = [
    path("", ProjectRoomsView.as_view()),
    path("<uuid:room_id>", ProjectRoomView.as_view()),
]

project_patterns = [
    path("", ProjectView.as_view()),
    path("/stats", ProjectStatsView.as_view()),
    path("/rooms/", include(room_patterns)),
    path("/teachers/", include(teacher_patterns)),
    path("/degrees/", include(degree_patterns)),
    path("/parallel-candidates", ProjectParallelBlockCandidateView.as_view()),
    path("/parallel-groups", ProjectParallelBlockGroupMembersView.as_view()),
]

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>", include(project_patterns)),
]
