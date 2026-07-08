"""Root URL configuration.

React SPA pages are served by ``spa_view``; API endpoints live under ``/api/``.
See docs/refactors/frontend.md for how React Router and Django URLs stay in sync.
"""

from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from src.projects.views.export import ProjectExportView

# SPA (Single Page Application) for React
spa_view = ensure_csrf_cookie(
    TemplateView.as_view(template_name="index.html"),
)

projectpatterns = [
    path("export/<int:project_id>", ProjectExportView.as_view()),
]

urlpatterns = [
    # React URLs
    path("", spa_view, name="dashboard"),
    path("login", spa_view, name="login"),
    path("forgot-password", spa_view, name="forgot-password"),
    path("change-password", spa_view, name="change-password"),
    path("projects/<int:project_id>/", spa_view, name="schedule"),
    path("projects/<int:project_id>/dashboard", spa_view, name="dashboard"),
    path(
        "projects/<int:project_id>/dashboard/export-session",
        spa_view,
        name="export-session-context",
    ),
    path(
        "projects/<int:project_id>/dashboard/degrees/<uuid:degree_id>",
        spa_view,
        name="degree-detail",
    ),
    path(
        "projects/<int:project_id>/dashboard/teachers/<uuid:teacher_id>",
        spa_view,
        name="teacher-detail",
    ),
    path(
        "projects/<int:project_id>/dashboard/rooms/<uuid:room_id>",
        spa_view,
        name="room-detail",
    ),
    path(
        "projects/<int:project_id>/dashboard/subjects/<uuid:subject_id>",
        spa_view,
        name="subject-detail",
    ),
    path(
        "projects/<int:project_id>/dashboard/classes/<uuid:class_id>",
        spa_view,
        name="class-detail",
    ),
    # API endpoints
    path("api/projects/", include("src.projects.urls")),
    path("api/auth/", include("src.login.urls")),
    path("admin/", admin.site.urls, name="admin"),  # TODO Check URL
    path("project/", include(projectpatterns)),
]
