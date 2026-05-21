import logging
import threading
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth
from src.core.errors import ApiError, ErrorResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.ingestion.manager import IngestionManager
from src.projects.models import Project
from src.projects.services.project_db import create_project_db, delete_project_db
from src.projects.views.schemas.project import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectResponse,
    ProjectsResponse,
    RenameProjectRequest,
)

logger = logging.getLogger(__name__)


class ProjectsView(View):
    """API endpoint: list all projects (GET) or create a new project (POST)."""

    @require_auth
    def get(self, request: HttpRequest) -> HttpResponse:
        # -- Fetch all projects ------------------------------------------------
        projects = list(Project.objects.order_by("-created_at"))
        response = SuccessResponse(
            message="Projects retrieved successfully",
            data=ProjectsResponse(projects=projects),
        )
        return JsonResponse(response.model_dump())

    @require_auth
    def post(self, request: HttpRequest) -> HttpResponse:
        # -- Validate and extract input ----------------------------------------
        validated, err = validate_request_body(CreateProjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        project_name = validated.name
        project_url = validated.url

        # -- Check if Project already exists -----------------------------------
        if Project.objects.filter(name=project_name).exists():
            return ErrorResponse(
                status=HTTPStatus.BAD_REQUEST,
                code=ApiError.PROJECTS_CREATE_DUPLICATED_NAME,
                message=f"A project with the name '{project_name}' already exists.",
            )

        # -- Create Project's entry and DB -------------------------------------
        proj = Project(name=project_name, url=str(project_url), creator=request.user)
        proj.save()
        proj_id: int = proj.pk

        try:
            create_project_db(proj_id)
        except Exception:
            proj.delete()
            return ErrorResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                code=ApiError.PROJECTS_CREATE_FAILED,
                message="Failed to create project.",
            )

        # -- Run Ingestion in a background thread ------------------------------
        def run() -> None:
            try:
                with IngestionManager(proj_id=proj_id) as manager:
                    manager.run()
            except Exception:
                logger.exception("Unhandled exception in background parse thread")

        threading.Thread(target=run, daemon=True).start()

        # -- Return success confirmation ---------------------------------------
        response = SuccessResponse(
            message="Project created successfully, ingestion started",
            data=CreateProjectResponse(
                id=proj_id,
                name=project_name,
            ),
        )
        return JsonResponse(response.model_dump(), status=HTTPStatus.ACCEPTED)


class ProjectView(View):
    """API endpoint: retrieve (GET), rename (PATCH), or delete (DELETE) a single project."""

    @require_auth
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Return project ----------------------------------------------------
        response = SuccessResponse(
            message="Project retrieved successfully",
            data=ProjectResponse.model_validate(project),
        )
        return JsonResponse(response.model_dump())

    @require_auth
    def patch(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Validate and extract input ----------------------------------------
        validated, err = validate_request_body(RenameProjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Check if name is taken --------------------------------------------
        new_name = validated.name
        if Project.objects.filter(name=new_name).exclude(pk=project_id).exists():
            return ErrorResponse(
                status=HTTPStatus.BAD_REQUEST,
                code=ApiError.PROJECTS_RENAME_DUPLICATED_NAME,
                message=f"A project with the name '{new_name}' already exists.",
            )

        # -- Rename and return -------------------------------------------------
        project.name = new_name
        project.save()

        return JsonResponse(
            SuccessResponse(
                message="Project renamed successfully",
                data=ProjectResponse.model_validate(project),
            ).model_dump(),
        )

    @require_auth
    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Delete project and its DB -----------------------------------------
        delete_project_db(project.pk)
        project.delete()

        return JsonResponse(
            {"message": "Project deleted successfully"},
            status=HTTPStatus.OK,
        )
