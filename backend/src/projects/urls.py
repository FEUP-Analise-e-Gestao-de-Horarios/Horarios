from django.urls import path

from src.projects.views import (
    ProjectClassesView,
    ProjectDegreesView,
    ProjectRoomsView,
    ProjectStatsView,
    ProjectSubjectsView,
    ProjectsView,
    ProjectTeachersView,
    ProjectView,
    ProjectYearsView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>", ProjectView.as_view()),
    path("<int:project_id>/stats", ProjectStatsView.as_view()),
    path("<int:project_id>/rooms/", ProjectRoomsView.as_view()),
    path("<int:project_id>/teachers/", ProjectTeachersView.as_view()),
    path("<int:project_id>/degrees/", ProjectDegreesView.as_view()),
    path("<int:project_id>/degrees/<uuid:degree_id>/years/", ProjectYearsView.as_view()),
    path(
        "<int:project_id>/degrees/<uuid:degree_id>/years/<uuid:year_id>/subjects/",
        ProjectSubjectsView.as_view(),
    ),
    path(
        "<int:project_id>/degrees/<uuid:degree_id>/years/<uuid:year_id>/classes/",
        ProjectClassesView.as_view(),
    ),
]
