import logging
import threading
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse
from src.core.schemas import SuccessResponse
from src.ingestion.manager import IngestionManager
from src.parser.utils import validate_request_body
from src.projects.models import Project
from src.projects.projects_db.dao import DegreeDAO, RoomDAO, StatsDAO, TeacherDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    DegreeStatsResponse,
    ProjectDegreesResponse,
    ProjectResponse,
    ProjectRoomsResponse,
    ProjectsResponse,
    ProjectStatsResponse,
    ProjectTeachersResponse,
    ProjectYearsResponse,
    RenameProjectRequest,
    RoomStatsResponse,
    TeacherStatsResponse,
    YearStatsResponse,
)
from src.projects.services.project_db import create_project_db, delete_project_db

logger = logging.getLogger(__name__)


class ProjectsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch all projects ------------------------------------------------
        projects = list(Project.objects.all())
        response = SuccessResponse(
            message="Projects retrieved successfully",
            data=ProjectsResponse(projects=projects, count=len(projects)),
        )
        return JsonResponse(response.model_dump())

    def post(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
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
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

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
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

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
        project.save(update_fields=["name"])

        return JsonResponse(
            SuccessResponse(
                message="Project renamed successfully",
                data=ProjectResponse.model_validate(project),
            ).model_dump(),
        )

    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

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


class ProjectDegreesView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query degrees with stats from project DB --------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = DegreeDAO(db_session).get_all_with_stats()
            result = [
                DegreeStatsResponse(
                    id=str(s.id),
                    acronym=s.acronym,
                    name=s.name,
                    num_years=s.num_years,
                    num_subjects=s.num_subjects,
                    num_classes=s.num_classes,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Degrees retrieved successfully",
                data=ProjectDegreesResponse(degrees=result, count=len(result)),
            ).model_dump(),
        )


class ProjectYearsView(View):
    def get(self, request: HttpRequest, project_id: int, degree_id: str) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query years with stats from project DB ----------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = YearDAO(db_session).get_by_degree_with_stats(degree_id)
            result = [
                YearStatsResponse(
                    id=str(s.id),
                    number=s.number,
                    degree_id=str(s.degree_id),
                    degree_acronym=s.degree_acronym,
                    degree_name=s.degree_name,
                    num_subjects=s.num_subjects,
                    num_classes=s.num_classes,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Years retrieved successfully",
                data=ProjectYearsResponse(years=result, count=len(result)),
            ).model_dump(),
        )


class ProjectRoomsView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query rooms with stats from project DB ----------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = RoomDAO(db_session).get_all_with_stats()
            result = [
                RoomStatsResponse(
                    id=str(s.id),
                    name=s.name,
                    type=s.type,
                    size=s.size,
                    seats=s.seats,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Rooms retrieved successfully",
                data=ProjectRoomsResponse(rooms=result, count=len(result)),
            ).model_dump(),
        )


class ProjectTeachersView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query teachers with stats from project DB -------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = TeacherDAO(db_session).get_all_with_stats()
            result = [
                TeacherStatsResponse(
                    id=str(s.id),
                    number=s.number,
                    acronym=s.acronym,
                    name=s.name,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Teachers retrieved successfully",
                data=ProjectTeachersResponse(teachers=result, count=len(result)),
            ).model_dump(),
        )


class ProjectStatsView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query overview stats from project DB ------------------------------
        with get_project_session(general_db(project_id)) as db_session:
            overview = StatsDAO(db_session).get_overview()

        return JsonResponse(
            SuccessResponse(
                message="Stats retrieved successfully",
                data=ProjectStatsResponse(
                    num_degrees=overview.num_degrees,
                    num_years=overview.num_years,
                    num_subjects=overview.num_subjects,
                    num_classes=overview.num_classes,
                    num_teachers=overview.num_teachers,
                    num_rooms=overview.num_rooms,
                    num_sessions=overview.num_sessions,
                ),
            ).model_dump(),
        )
