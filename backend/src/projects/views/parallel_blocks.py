from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    InvalidBodyResponse,
    ParallelGroupInvalidCandidatesResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.projects.models import Project
from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_block_group_dao import ParallelBlockGroupDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.parallel_blocks import (
    ParallelCandidateGroupResponse,
    ParallelGroupResponse,
    SaveParallelGroupMembersRequest,
)


class ProjectParallelBlockCandidateView(View):
    """API endpoint: list parallel classes."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            parallel_block_candidate_dao = ParallelBlockCandidateDAO(db_session)

            groups = parallel_block_candidate_dao.get_all_groups_with_info()

            return JsonResponse(
                SuccessResponse(
                    message="Candidate parallel groups retrieved successfully",
                    data=[ParallelCandidateGroupResponse.model_validate(group) for group in groups],
                ).model_dump(),
            )


class ProjectParallelBlockGroupsView(View):
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
                    data=[
                        ParallelGroupResponse(group_id=group_id, block_ids=block_ids)
                        for group_id, block_ids in groups.items()
                    ],
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
            components = {
                component.candidate_group_id: component
                for component in ParallelBlockCandidateDAO(db_session).get_candidate_components()
            }

            for entry in validated.groups:
                blocks = set(entry.block_ids)
                if len(blocks) < 2:
                    continue
                component = components.get(entry.candidate_group_id)
                if component is None or not component.is_connected_subset(blocks):
                    return ParallelGroupInvalidCandidatesResponse()

            dao = ParallelBlockGroupDAO(db_session)
            dao.clear_all()

            assigned = 0
            try:
                for entry in validated.groups:
                    if len(entry.block_ids) < 2:
                        continue
                    dao.create(entry.block_ids)
                    assigned += 1
            except ValueError as exc:
                return InvalidBodyResponse(str(exc))

            db_session.commit()

            Project.objects.filter(pk=project_id).update(has_selected_parallel_sessions=True)

            return JsonResponse(
                SuccessResponse(
                    message="Parallel group members saved successfully",
                    data=assigned,
                ).model_dump(),
            )
