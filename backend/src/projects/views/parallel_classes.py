import logging
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao.degree_dao import DegreeDAO
from src.projects.projects_db.dao.subject_dao import SubjectDAO
from src.projects.projects_db.dao.year_dao import YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.parallel_classes import (
    DegreeListResponse,
    DegreeResponse,
    SubjectListResponse,
    SubjectResponse,
    YearListResponse,
    YearResponse,
)

logger = logging.getLogger(__name__)


class ProjectsParallelDegreeListView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            degrees = DegreeDAO(db_session).get_with_parallel_classes()

            data = [
                DegreeResponse.model_validate(degree, from_attributes=True).model_dump()
                for degree in degrees
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Degrees with parallel classes retrieved successfully",
                    data=DegreeListResponse(
                        count=len(data),
                        degrees=data,
                    ),
                ).model_dump(),
            )


class ProjectsParallelYearListView(View):
    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            years = YearDAO(db_session).get_with_parallel_classes(degree_id=degree_id)

            data = [
                YearResponse.model_validate(year, from_attributes=True).model_dump()
                for year in years
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Years with parallel classes retrieved successfully",
                    data=YearListResponse(
                        count=len(data),
                        years=data,
                    ),
                ).model_dump(),
            )


class ProjectsParallelSubjectListView(View):
    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            subjects = SubjectDAO(db_session).get_with_parallel_classes(year_id=year_id)

            data = [
                SubjectResponse.model_validate(subject, from_attributes=True).model_dump()
                for subject in subjects
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Subjects with parallel classes retrieved successfully",
                    data=SubjectListResponse(
                        count=len(data),
                        subjects=data,
                    ),
                ).model_dump(),
            )


# @csrf_exempt
# def guardar_aulas_em_paralelo(request: HttpRequest) -> JsonResponse:
#    if not request.user.is_authenticated:
#        return JsonResponse({"error": "User is not authenticated"}, status=401)
#
#    project_id_raw = request.GET.get("id")
#    if project_id_raw is None:
#        return JsonResponse({"error": "Invalid project ID"}, status=400)
#    try:
#        project_id = int(project_id_raw)
#    except ValueError:
#        return JsonResponse({"error": "Invalid project ID"}, status=400)
#
#    try:
#        project = Project.objects.get(id=project_id)
#    except Project.DoesNotExist:
#        return JsonResponse({"error": "Project not found"}, status=404)
#
#    person = request.user
#    user_groups = set(person.member_groups.values_list("id", flat=True))
#    project_groups = set(project.group.values_list("id", flat=True))
#
#    if not (
#        project.creator == person
#        or request.user.is_staff
#        or project.people.filter(pk=person.pk).exists()
#        or bool(user_groups & project_groups)
#    ):
#        return JsonResponse({"error": "Forbidden"}, status=403)
#
#    try:
#        validated, err = validate_request_body(AulasSimultaneasInput, request.body)
#        if err:
#            return err
#        assert validated is not None
#
#        db_path = Path(settings.PROJECTS_DB_PATH) / str(project_id) / "general_database.db"
#
#        with sqlite3.connect(db_path, timeout=10) as conn:
#            conn.row_factory = sqlite3.Row
#            cursor = conn.cursor()
#            cursor.execute("DELETE FROM turmasSimultaneas")
#            for par in validated.pares:
#                cursor.execute(
#                    """
#                    INSERT INTO turmasSimultaneas (aula1, aula2, turma1, turma2)
#                    VALUES (?, ?, ?, ?)
#                    """,
#                    (par.aula1, par.aula2, par.turma1, par.turma2),
#                )
#            conn.commit()
#
#            inconsistentes = check_parallel_classes(cursor, validated.pares)
#
#            project.has_selected_aulas_em_paralelo = True
#            project.save()
#
#            return JsonResponse({"status": "ok", "inconsistentes": inconsistentes})
#
#    except Exception as e:
#        return JsonResponse({"status": "erro", "message": str(e)}, status=500)
#
