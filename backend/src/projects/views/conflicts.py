import json
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.projects.projects_db.dao import ConflictDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.services.conflict_detection import get_live_conflicts
from src.projects.services.conflict_preview import preview_conflict_changes
from src.projects.views.schemas.conflicts import (
    ConflictPreviewRequest,
    ConflictPreviewResponse,
    ConflictsResponse,
    UpdateConflictTagRequest,
)


class ProjectConflictsView(View):
    """List all live conflicts for the project, with stored tags applied."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            sessions = SessionDAO(db_session).get_all(includes=list(SessionDAO.Include))
            conflicts = get_live_conflicts(db_session, sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Conflicts retrieved successfully",
                    data=ConflictsResponse(conflicts=conflicts, count=len(conflicts)),
                ).model_dump(),
            )


class ProjectConflictView(View):
    """Operate on a single conflict group (identified by conflict_id)."""

    @require_auth
    @require_project
    def patch(self, request: HttpRequest, project_id: int, conflict_id: UUID) -> HttpResponse:
        try:
            body = UpdateConflictTagRequest.model_validate(json.loads(request.body))
        except Exception:
            return JsonResponse({"error": "Invalid request body"}, status=400)

        with get_project_session(general_db(project_id)) as db_session:
            ConflictDAO(db_session).update_tag(conflict_id, body.tag)
            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Conflict tag updated successfully",
                    data=None,
                ).model_dump(),
            )


class ProjectConflictPreviewView(View):
    """Return which conflicts a hypothetical session edit would solve or create."""

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        body, err = validate_request_body(ConflictPreviewRequest, request.body)
        if err:
            return err

        with get_project_session(general_db(project_id)) as db_session:
            solved, new = preview_conflict_changes(
                db_session=db_session,
                original_block_id=body.original_block_id,
                new_weekday=body.weekday,
                new_start_time=body.start_time,
                new_duration=body.duration,
                new_teacher_ids=body.teacher_ids,
                new_room_ids=body.room_ids,
                new_class_ids=body.class_ids,
            )

            return JsonResponse(
                SuccessResponse(
                    message="Conflict preview computed successfully",
                    data=ConflictPreviewResponse(solved=solved, new=new),
                ).model_dump(),
            )
