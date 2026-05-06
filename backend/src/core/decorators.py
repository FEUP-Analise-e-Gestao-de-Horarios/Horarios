from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.projects.models import Project

ViewMethod = Callable[..., HttpResponse]


def require_auth(view_method: ViewMethod) -> ViewMethod:
    """Return 401 if the request user is not authenticated."""

    @wraps(view_method)
    def wrapper(self: Any, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()
        return view_method(self, request, *args, **kwargs)

    return wrapper


def require_project(view_method: ViewMethod) -> ViewMethod:
    """Return 404 if the URL's `project_id` does not match an existing project."""

    @wraps(view_method)
    def wrapper(self: Any, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not Project.objects.filter(pk=kwargs["project_id"]).exists():
            return ProjectNotFoundResponse()
        return view_method(self, request, *args, **kwargs)

    return wrapper
