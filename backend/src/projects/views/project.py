import logging
import threading
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse, NotAuthenticatedResponse
from src.core.schemas import SuccessResponse
from src.ingestion.manager import IngestionManager
from src.parser.utils import validate_request_body
from src.projects.models import Project
from src.projects.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectResponse,
    ProjectsResponse,
    RenameProjectRequest,
)
from src.projects.services.project_db import create_project_db, delete_project_db

logger = logging.getLogger(__name__)


class ProjectsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch all projects ------------------------------------------------
        projects = list(Project.objects.order_by("-created_at"))
        response = SuccessResponse(
            message="Projects retrieved successfully",
            data=ProjectsResponse(projects=projects, count=len(projects)),
        )
        return JsonResponse(response.model_dump())

    def post(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

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
                IngestionManager(proj_id=proj_id).run()
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
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Return project ----------------------------------------------------
        response = SuccessResponse(
            message="Project retrieved successfully",
            data=ProjectResponse.model_validate(project),
        )
        return JsonResponse(response.model_dump())

    def patch(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Validate and extract input ----------------------------------------
        validated, err = validate_request_body(RenameProjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

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

    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Delete project and its DB -----------------------------------------
        delete_project_db(project.pk)
        project.delete()

        return JsonResponse(
            {"message": "Project deleted successfully"},
            status=HTTPStatus.OK,
        )
