from time import time
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.exporter.export_graph import ExportGraph
from src.projects.models import Project
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session


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
        # with Comparator(project_id) as comp:
        #     start_time = time()
        #     data = comp.database_differences()

        #     data.update(comp.database_conflicts())
        #     end_time = time()

        #     print(f"time elapsed: {'%.2f' % (end_time - start_time)}")

        #     return JsonResponse(
        #         SuccessResponse(
        #             message="Project export computed successfully",
        #             data=data,
        #         ).model_dump(),
        #     )

        with get_session(general_db(project_id)) as session:
            session_dao = SessionDAO(session)
            rooms_dao = RoomDAO(session)
            teachers_dao = TeacherDAO(session)
            class_dao = ClassDAO(session)

            start_time = time()
            alias = session_dao.attach_db(initial_db(project_id))
            data: dict[str, Any] = {}
            modifications = session_dao.get_changes_only(alias)
            data.update({"modified_sessions": modifications})
            data.update({"added_removed_sessions": session_dao.get_added_removed_records(alias)})
            data.update({"rooms_conflicts": rooms_dao.get_conflicting_slots()})
            data.update({"teacher_conflicts": teachers_dao.get_conflicting_slots()})
            data.update({"classes_conflicts": class_dao.get_conflicting_slots()})
            session_dao.detach_db(alias)
            end_time = time()
            export_graph = ExportGraph(modifications, project_id)
            export_graph.build_graph()
            modification_groups = export_graph.order_change_groups_using_graph()
            dependencies = export_graph.get_dependencies()
            data.update(
                {
                    "modification_steps": [
                        {
                            "type": "exchange" if len(group) > 1 else "move",
                            "sessions": {
                                str(session_id): modifications[str(session_id)]
                                for session_id in group
                            },
                        }
                        for group in modification_groups
                    ],
                    "modifications_dependencies": dependencies,
                },
            )

            print(f"time elapsed: {'%.2f' % (end_time - start_time)}")

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=data,
                ).model_dump(),
            )
