from time import time

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.exporter.differences import Comparator
from src.projects.models import Project
from src.projects.views.schemas.export import ProjectExportResponse


class ProjectExportView(View):
    """API endpoint: compute the diff and conflicts between a project's
    initial and current databases."""

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Compute differences and conflicts ---------------------------------
        with Comparator(project_id) as comp:
            start_time = time()
            data = comp.database_differences()

            data.update(comp.database_conflicts())
            end_time = time()

            print(f"time elapsed: {'%.2f' % (end_time - start_time)}")

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=ProjectExportResponse.model_validate(data),
                ).model_dump(),
            )
        # with get_session(general_db(project_id)) as session:
        #     session_dao = SessionDAO(session)
        #     rooms_dao = RoomDAO(session)
        #     teachers_dao = TeacherDAO(session)
        #     class_dao = ClassDAO(session)

        #     start_time = time()
        #     alias = session_dao.attach_db(initial_db(project_id))
        #     data = session_dao.get_changes_only(alias)
        #     data.update({"rooms_conflicts": rooms_dao.get_conflicting_slots()})
        #     data.update({"teacher_conflicts": teachers_dao.get_conflicting_slots()})
        #     data.update({"classes_conflicts": class_dao.get_conflicting_slots()})
        #     session_dao.detach_db(alias)
        #     end_time = time()

        #     print(f"time elapsed: {"%.2f" % (end_time - start_time)}")

        #     return JsonResponse(
        #         SuccessResponse(
        #             message="Project export computed successfully",
        #             data=data,
        #         ).model_dump(),
        #     )
