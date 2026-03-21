from django.urls import path

from src.projects.views import ProjectDegreesView, ProjectsView, ProjectView, ProjectYearsView

app_name = "projects"

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>/", ProjectView.as_view()),
    path("<int:project_id>/degrees/", ProjectDegreesView.as_view()),
    path("<int:project_id>/degrees/<uuid:degree_id>/years/", ProjectYearsView.as_view()),
]
