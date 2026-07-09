import json
from collections.abc import Mapping
from time import time
from typing import cast
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from pydantic import BaseModel

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.exporter.compact_payload import (
    COMPACT_EXPORT_FORMAT,
    compact_export_payload,
    expand_compact_export_payload,
)
from src.exporter.export_graph import ExportGraph
from src.exporter.schemas import (
    CompactProjectExportPayload,
    ExportJsonValue,
    ExportPayload,
    PayloadFormat,
    ProjectExportPayload,
)
from src.projects.models import Project
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.export_cache_dao import ExportCacheDAO
from src.projects.projects_db.dao.export_checklist_dao import ExportChecklistDAO
from src.projects.projects_db.dao.export_state_dao import ExportStateDAO
from src.projects.projects_db.dao.modified_session_dao import ModifiedSessionDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session, init_engine
from src.projects.views.schemas.shared import RedBlockBase
from src.projects.views.schemas.week_blocks import WeekBlock


class ExportSessionContextResource(BaseModel):
    id: UUID
    kind: str
    title: str
    subtitle: str
    blocks: list[WeekBlock]
    red_blocks: list[RedBlockBase]


class ExportSessionContextPayload(BaseModel):
    classes: list[ExportSessionContextResource]
    rooms: list[ExportSessionContextResource]
    teachers: list[ExportSessionContextResource]


class ProjectExportChecklistPayload(BaseModel):
    item_key: str
    checked: bool


class ProjectExportChecklistResponse(BaseModel):
    checked_item_keys: list[str]


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
        request_payload_format = payload.get("payload_format")
        payload_format: PayloadFormat = (
            request_payload_format
            if request_payload_format in {"compact", "expanded"}
            else "compact"
        )

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
        init_engine(initial_db(project_id))

        export_is_dirty = self.is_project_export_dirty(project_id)
        with get_session(general_db(project_id)) as session:
            export_cache_dao = ExportCacheDAO(session)
            export_checklist_dao = ExportChecklistDAO(session)
            if not recalculate_export_graph and not export_is_dirty:
                cached_data = export_cache_dao.get_project_export_payload()
                if cached_data is not None:
                    if cached_data.get("format") == COMPACT_EXPORT_FORMAT:
                        if self.cached_payload_supports_added_removed_navigation(cached_data):
                            cached_data["checked_item_keys"] = (
                                export_checklist_dao.get_checked_item_keys()
                            )
                            response_data = self.format_export_payload(cached_data, payload_format)
                            return JsonResponse(
                                SuccessResponse(
                                    message="Project export loaded from cache",
                                    data=response_data,
                                ).model_dump(),
                            )

                        export_cache_dao.clear_project_export_payload()
                        ModifiedSessionDAO(session).clear_modification_steps()
                        session.commit()
                    else:
                        export_cache_dao.clear_project_export_payload()
                        ModifiedSessionDAO(session).clear_modification_steps()
                        session.commit()
                elif export_cache_dao.has_project_export_payload():
                    export_cache_dao.clear_project_export_payload()
                    ModifiedSessionDAO(session).clear_modification_steps()
                    session.commit()

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
            added_removed_sessions = session_dao.get_added_removed_records(alias)
            rooms_conflicts = rooms_dao.get_conflicting_slots()
            teacher_conflicts = teachers_dao.get_conflicting_slots()
            classes_conflicts = class_dao.get_conflicting_slots()

            if cached_modification_steps:
                modification_steps = cached_modification_steps
            else:
                modifications = session_dao.get_changes_only(alias)
                export_graph = ExportGraph(modifications, project_id)
                modification_steps = export_graph.build_modification_steps()
                modified_session_dao.replace_modification_steps(modification_steps)

            session_dao.detach_db(alias)
            end_time = time()

            data = ProjectExportPayload.model_validate(
                {
                    "added_removed_sessions": added_removed_sessions,
                    "rooms_conflicts": rooms_conflicts,
                    "teacher_conflicts": teacher_conflicts,
                    "classes_conflicts": classes_conflicts,
                    "modification_steps": modification_steps,
                    "checked_item_keys": export_checklist_dao.get_checked_item_keys(),
                },
            )
            compact_data = compact_export_payload(data)
            export_cache_dao.replace_project_export_payload(compact_data)
            ExportStateDAO(session).mark_project_export_clean()
            session.commit()
            self.mark_initial_export_clean(project_id)

            print(f"time elapsed: {'%.2f' % (end_time - start_time)}")

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=self.format_export_payload(compact_data, payload_format),
                ).model_dump(),
            )

    @staticmethod
    def is_project_export_dirty(project_id: int) -> bool:
        for db_path in (general_db(project_id), initial_db(project_id)):
            with get_session(db_path) as session:
                if ExportStateDAO(session).is_project_export_dirty():
                    return True
        return False

    @staticmethod
    def mark_initial_export_clean(project_id: int) -> None:
        with get_session(initial_db(project_id)) as session:
            ExportStateDAO(session).mark_project_export_clean()
            session.commit()

    @staticmethod
    def format_export_payload(
        data: ExportPayload | Mapping[str, ExportJsonValue],
        payload_format: PayloadFormat,
    ) -> dict[str, ExportJsonValue]:
        if isinstance(data, BaseModel):
            model = data
        elif data.get("format") == COMPACT_EXPORT_FORMAT:
            model = CompactProjectExportPayload.model_validate(data)
        else:
            model = ProjectExportPayload.model_validate(data)

        if isinstance(model, CompactProjectExportPayload):
            if payload_format == "compact":
                return cast(dict[str, ExportJsonValue], model.model_dump(mode="json"))
            return cast(
                dict[str, ExportJsonValue],
                expand_compact_export_payload(model).model_dump(mode="json"),
            )

        if payload_format == "compact":
            return cast(
                dict[str, ExportJsonValue],
                compact_export_payload(model).model_dump(mode="json"),
            )
        return cast(dict[str, ExportJsonValue], model.model_dump(mode="json"))

    @staticmethod
    def cached_payload_supports_added_removed_navigation(
        data: Mapping[str, ExportJsonValue],
    ) -> bool:
        records = data.get("added_removed_sessions")
        if not isinstance(records, Mapping):
            return False

        added = records.get("added", [])
        removed = records.get("removed", [])
        if not isinstance(added, list) or not isinstance(removed, list):
            return False

        rows = [*added, *removed]
        for row in rows:
            if not isinstance(row, Mapping):
                return False
            has_target = bool(row.get("class_ids") or row.get("room_ids") or row.get("teacher_ids"))
            if not (
                has_target
                and row.get("week")
                and row.get("weekday")
                and row.get("start_time") is not None
                and row.get("duration") is not None
            ):
                return False

        return True


class ProjectExportChecklistView(View):
    """API endpoint: persist checked exporter work items."""

    def patch(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        try:
            raw_payload = json.loads(request.body or b"{}")
            payload = ProjectExportChecklistPayload.model_validate(raw_payload)
        except json.JSONDecodeError, ValueError:
            return JsonResponse({"message": "Invalid checklist payload."}, status=400)

        init_engine(general_db(project_id))
        with get_session(general_db(project_id)) as session:
            checked_item_keys = ExportChecklistDAO(session).set_checked(
                payload.item_key,
                payload.checked,
            )
            session.commit()

        return JsonResponse(
            SuccessResponse(
                message="Export checklist updated successfully",
                data=ProjectExportChecklistResponse(checked_item_keys=checked_item_keys),
            ).model_dump(mode="json"),
        )

    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        init_engine(general_db(project_id))
        with get_session(general_db(project_id)) as session:
            checked_item_keys = ExportChecklistDAO(session).clear_checked_items()
            session.commit()

        return JsonResponse(
            SuccessResponse(
                message="Export checklist cleared successfully",
                data=ProjectExportChecklistResponse(checked_item_keys=checked_item_keys),
            ).model_dump(mode="json"),
        )


class ProjectExportSessionContextView(View):
    """API endpoint: fetch dashboard context for an added or removed export session."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        db_path = (
            initial_db(project_id)
            if request.GET.get("exportSessionChange") == "removed"
            else general_db(project_id)
        )

        with get_session(db_path) as session:
            session_dao = SessionDAO(session)
            includes = list(SessionDAO.Include)

            class_resources: list[ExportSessionContextResource] = []
            class_dao = ClassDAO(session)
            for class_id in self.parse_uuid_list(request.GET.get("exportSessionClassIds")):
                class_ = class_dao.get(class_id)
                if class_ is None:
                    continue
                class_resources.append(
                    ExportSessionContextResource(
                        id=class_.id,
                        kind="class",
                        title=class_.code,
                        subtitle=" · ".join(
                            filter(
                                None,
                                [
                                    class_.year.degree.name if class_.year else "",
                                    f"{class_.year.number}º ano" if class_.year else "",
                                ],
                            ),
                        ),
                        blocks=WeekBlock.from_sessions(
                            session_dao.get_by_class(class_id, includes=includes),
                        ),
                        red_blocks=[
                            RedBlockBase.model_validate(red_block)
                            for red_block in class_.red_blocks
                        ],
                    ),
                )

            room_resources: list[ExportSessionContextResource] = []
            room_dao = RoomDAO(session)
            for room_id in self.parse_uuid_list(request.GET.get("exportSessionRoomIds")):
                room = room_dao.get(room_id)
                if room is None:
                    continue
                room_resources.append(
                    ExportSessionContextResource(
                        id=room.id,
                        kind="room",
                        title=room.name,
                        subtitle=" · ".join(
                            filter(
                                None,
                                [
                                    room.type or "",
                                    room.size or "",
                                    f"{room.seats} lugares" if room.seats else "",
                                ],
                            ),
                        ),
                        blocks=WeekBlock.from_sessions(
                            session_dao.get_by_room(room_id, includes=includes),
                        ),
                        red_blocks=[
                            RedBlockBase.model_validate(red_block) for red_block in room.red_blocks
                        ],
                    ),
                )

            teacher_resources: list[ExportSessionContextResource] = []
            teacher_dao = TeacherDAO(session)
            for teacher_id in self.parse_uuid_list(request.GET.get("exportSessionTeacherIds")):
                teacher = teacher_dao.get(teacher_id)
                if teacher is None:
                    continue
                teacher_resources.append(
                    ExportSessionContextResource(
                        id=teacher.id,
                        kind="teacher",
                        title=teacher.acronym or teacher.name,
                        subtitle=teacher.name,
                        blocks=WeekBlock.from_sessions(
                            session_dao.get_by_teacher(teacher_id, includes=includes),
                        ),
                        red_blocks=[
                            RedBlockBase.model_validate(red_block)
                            for red_block in teacher.red_blocks
                        ],
                    ),
                )

        return JsonResponse(
            SuccessResponse(
                message="Export session context retrieved successfully",
                data=ExportSessionContextPayload(
                    classes=class_resources,
                    rooms=room_resources,
                    teachers=teacher_resources,
                ),
            ).model_dump(mode="json"),
        )

    @staticmethod
    def parse_uuid_list(value: str | None) -> list[UUID]:
        parsed: list[UUID] = []
        for item in (value or "").split(","):
            item = item.strip()
            if not item:
                continue
            try:
                parsed.append(UUID(item))
            except ValueError:
                continue
        return parsed
