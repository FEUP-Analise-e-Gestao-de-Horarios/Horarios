import logging
import threading
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.schemas import SuccessResponse
from src.ingestion.manager import IngestionManager
from src.parser.utils import validate_request_body
from src.projects.models import Project
from src.projects.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectsResponse,
    RenameProjectRequest,
)
from src.projects.services.project_db import create_project_db, delete_project_db

logger = logging.getLogger(__name__)


class ProjectsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        projects = list(Project.objects.all())
        response = SuccessResponse(
            message="Projects retrieved successfully",
            data=ProjectsResponse(projects=projects, count=len(projects)),
        )
        return JsonResponse(response.model_dump())

    def post(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "User is not authenticated"},
                status=HTTPStatus.UNAUTHORIZED,
            )

        # -- Validate and extract input ----------------------------------------
        validated, err = validate_request_body(CreateProjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        project_name = validated.name
        project_url = validated.url

        # -- Check if Project already exists -----------------------------------
        if Project.objects.filter(name=project_name).exists():
            return JsonResponse(
                {"error": f"A project with the name '{project_name}' already exists"},
                status=HTTPStatus.BAD_REQUEST,
            )

        # -- Create Project's entry and DB -------------------------------------
        proj = Project(name=project_name, url=str(project_url), creator=request.user)
        proj.save()
        proj_id: int = proj.pk

        try:
            create_project_db(proj_id)
        except Exception:
            proj.delete()
            return JsonResponse(
                {"error": "Failed to create project"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
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
    def patch(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "User is not authenticated"},
                status=HTTPStatus.UNAUTHORIZED,
            )

        validated, err = validate_request_body(RenameProjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"error": "Project not found"},
                status=HTTPStatus.NOT_FOUND,
            )

        new_name = validated.name
        if Project.objects.filter(name=new_name).exclude(pk=project_id).exists():
            return JsonResponse(
                {"error": f"A project with the name '{new_name}' already exists"},
                status=HTTPStatus.BAD_REQUEST,
            )

        project.name = new_name
        project.save(update_fields=["name"])

        return JsonResponse(
            SuccessResponse(
                message="Project renamed successfully",
                data={"id": project.pk, "name": project.name},
            ).model_dump(),
        )

    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "User is not authenticated"},
                status=HTTPStatus.UNAUTHORIZED,
            )

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"error": "Project not found"},
                status=HTTPStatus.NOT_FOUND,
            )

        delete_project_db(project.pk)
        project.delete()

        return JsonResponse(
            {"message": "Project deleted successfully"},
            status=HTTPStatus.OK,
        )
