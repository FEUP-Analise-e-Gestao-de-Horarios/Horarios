from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    ApiError,
    ErrorResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.projects.models import Project
from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_block_group_dao import ParallelBlockGroupDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.parallel_block_group_members import SaveParallelGroupMembersRequest


class ProjectParallelBlockGroupMembersView(View):
    """API endpoint: fetch and save confirmed parallel block groups."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            dao = ParallelBlockGroupDAO(db_session)
            groups = dao.get_all_groups()

        return JsonResponse(
            SuccessResponse(
                message="Parallel group members retrieved successfully",
                data={
                    str(group_id): [str(block_id) for block_id in block_ids]
                    for group_id, block_ids in groups.items()
                },
            ).model_dump(),
        )

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:

        validated, err = validate_request_body(SaveParallelGroupMembersRequest, request.body)
        if err:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            block_to_group = {
                block_id: group_id
                for group_id, block_ids in ParallelBlockCandidateDAO(db_session)
                .get_all_groups()
                .items()
                for block_id in block_ids
            }

            for entry in validated.groups:
                if len(entry.classes) < 2:
                    continue
                candidate_groups = {block_to_group.get(block_id) for block_id in entry.classes}
                if None in candidate_groups or len(candidate_groups) > 1:
                    return ErrorResponse(
                        status=400,
                        code=ApiError.PARALLEL_GROUPS_INVALID_CANDIDATES,
                        message="Some classes are not parallel candidates.",
                    )

            dao = ParallelBlockGroupDAO(db_session)
            dao.clear_all()

            assigned = 0
            try:
                for entry in validated.groups:
                    if len(entry.classes) < 2:
                        continue
                    dao.create(entry.classes)
                    assigned += 1
            except ValueError as exc:
                return ErrorResponse(
                    status=400,
                    code=ApiError.INVALID_BODY,
                    message=str(exc),
                )

            db_session.commit()

            Project.objects.filter(pk=project_id).update(has_selected_parallel_sessions=True)

            return JsonResponse(
                SuccessResponse(
                    message="Parallel group members saved successfully",
                    data=assigned,
                ).model_dump(),
            )
