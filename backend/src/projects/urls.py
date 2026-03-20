from django.urls import path

from src.projects.views import ProjectView, ProjectsView

app_name = "projects"

urlpatterns = [
    path("", ProjectsView.as_view()),
    path("<int:project_id>/", ProjectView.as_view()),
]
