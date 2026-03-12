from django.urls import path

from src.projects.views import ProjectsView

app_name = "projects"

urlpatterns = [
    path("", ProjectsView.as_view()),
]
