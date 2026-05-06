from django.urls import include, path

from src.projects.views import (
    ProjectClassesView,
    ProjectClassView,
    ProjectDegreesView,
    ProjectDegreeView,
    ProjectDegreeYearsView,
    ProjectRoomsView,
    ProjectRoomView,
    ProjectStatsView,
    ProjectSubjectsView,
    ProjectSubjectView,
    ProjectsView,
    ProjectTeachersView,
    ProjectTeacherView,
    ProjectView,
    ProjectYearsView,
    ProjectYearView,
)

app_name = "projects"

degree_year_patterns = [
    path("", ProjectDegreeYearsView.as_view()),
    path("<uuid:year_id>/subjects/", ProjectSubjectsView.as_view()),
    path("<uuid:year_id>/classes/", ProjectClassesView.as_view()),
]

year_patterns = [
    path("", ProjectYearsView.as_view()),
    path("<uuid:year_id>", ProjectYearView.as_view()),
]

degree_patterns = [
    path("", ProjectDegreesView.as_view()),
    path("<uuid:degree_id>", ProjectDegreeView.as_view()),
    path("<uuid:degree_id>/years/", include(degree_year_patterns)),
]

teacher_patterns = [
    path("", ProjectTeachersView.as_view()),
    path("<uuid:teacher_id>", ProjectTeacherView.as_view()),
]

room_patterns = [
    path("", ProjectRoomsView.as_view()),
    path("<uuid:room_id>", ProjectRoomView.as_view()),
]

subject_patterns = [
    path("<uuid:subject_id>", ProjectSubjectView.as_view()),
]

class_patterns = [
    path("<uuid:class_id>", ProjectClassView.as_view()),
]

project_patterns = [
    path("", ProjectView.as_view()),
    path("/stats", ProjectStatsView.as_view()),
    path("/rooms/", include(room_patterns)),
    path("/teachers/", include(teacher_patterns)),
    path("/degrees/", include(degree_patterns)),
    path("/years/", include(year_patterns)),
    path("/subjects/", include(subject_patterns)),
    path("/classes/", include(class_patterns)),
]

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>", include(project_patterns)),
]
