import json
from time import time
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.exporter.export_graph import ExportGraph
from src.projects.models import Project
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.export_cache_dao import ExportCacheDAO
from src.projects.projects_db.dao.modified_session_dao import ModifiedSessionDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session, init_engine


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

        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        recalculate_export_graph = bool(payload.get("recalculate_export_graph"))

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

        init_engine(general_db(project_id))

        with get_session(general_db(project_id)) as session:
            export_cache_dao = ExportCacheDAO(session)
            if not recalculate_export_graph:
                cached_data = export_cache_dao.get_project_export_payload()
                if cached_data is not None:
                    return JsonResponse(
                        SuccessResponse(
                            message="Project export loaded from cache",
                            data=cached_data,
                        ).model_dump(),
                    )

            session_dao = SessionDAO(session)
            modified_session_dao = ModifiedSessionDAO(session)
            rooms_dao = RoomDAO(session)
            teachers_dao = TeacherDAO(session)
            class_dao = ClassDAO(session)
            cached_modification_steps = (
                []
                if recalculate_export_graph
                else modified_session_dao.get_cached_modification_steps()
            )

            start_time = time()
            alias = session_dao.attach_db(initial_db(project_id))
            data: dict[str, Any] = {}
            data.update(
                {"added_removed_sessions": session_dao.get_added_removed_records(alias)},
            )
            data.update({"rooms_conflicts": rooms_dao.get_conflicting_slots()})
            data.update({"teacher_conflicts": teachers_dao.get_conflicting_slots()})
            data.update({"classes_conflicts": class_dao.get_conflicting_slots()})

            if cached_modification_steps:
                modification_steps = cached_modification_steps
            else:
                modifications = session_dao.get_changes_only(alias)
                export_graph = ExportGraph(modifications, project_id)
                modification_steps = export_graph.build_modification_steps()
                modified_session_dao.replace_modification_steps(modification_steps)

            session_dao.detach_db(alias)
            end_time = time()

            data.update(
                {
                    "modification_steps": modification_steps,
                },
            )
            export_cache_dao.replace_project_export_payload(data)
            session.commit()

            print(f"time elapsed: {'%.2f' % (end_time - start_time)}")

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=data,
                ).model_dump(),
            )
