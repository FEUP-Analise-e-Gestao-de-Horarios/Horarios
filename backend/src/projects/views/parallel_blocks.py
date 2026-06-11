from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    InvalidBodyResponse,
    ParallelGroupInvalidCandidatesResponse,
    ParallelGroupNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.projects.models import Project
from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_block_group_dao import ParallelBlockGroupDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.projects_db.schemas.parallel_candidates import ParallelBlockCandidateFilters
from src.projects.views.schemas.parallel_block_group_members import SaveParallelGroupMembersRequest


class ProjectParallelBlockCandidateView(View):
    """API endpoint: list parallel classes."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:

        year_id = request.GET.get("year_id")
        degree_id = request.GET.get("degree_id")
        subject_id = request.GET.get("subject_id")
        class_id = request.GET.get("class_id")
        start_time = request.GET.get("start_time")

        filters = ParallelBlockCandidateFilters(
            year_id=UUID(year_id) if year_id else None,
            degree_id=UUID(degree_id) if degree_id else None,
            subject_id=UUID(subject_id) if subject_id else None,
            class_id=UUID(class_id) if class_id else None,
            start_time=start_time or None,
        )

        with get_project_session(general_db(project_id)) as db_session:
            parallel_block_candidate_dao = ParallelBlockCandidateDAO(db_session)

            result = parallel_block_candidate_dao.get_all_groups_with_info(filters)

            return JsonResponse(
                SuccessResponse(
                    message="Candidate parallel groups retrieved successfully",
                    data=[group.model_dump(mode="json") for group in result],
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
                    return ParallelGroupInvalidCandidatesResponse()

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
                return InvalidBodyResponse(str(exc))

            db_session.commit()

            Project.objects.filter(pk=project_id).update(has_selected_parallel_sessions=True)

            return JsonResponse(
                SuccessResponse(
                    message="Parallel group members saved successfully",
                    data=assigned,
                ).model_dump(),
            )


class ProjectParallelBlockGroupView(View):
    """API endpoint: delete a confirmed parallel block group."""

    @require_auth
    @require_project
    def delete(self, request: HttpRequest, project_id: int, group_id: UUID) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            dao = ParallelBlockGroupDAO(db_session)
            if not dao.delete_group(group_id):
                return ParallelGroupNotFoundResponse()

            db_session.commit()

        return JsonResponse(
            SuccessResponse(
                message="Parallel group deleted successfully",
                data=None,
            ).model_dump(),
        )


class ProjectParallelBlockGroupMemberView(View):
    """API endpoint: remove a single block from a confirmed parallel block group."""

    @require_auth
    @require_project
    def delete(
        self,
        request: HttpRequest,
        project_id: int,
        group_id: UUID,
        block_id: UUID,
    ) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            dao = ParallelBlockGroupDAO(db_session)
            if not dao.remove_member(group_id, block_id):
                return ParallelGroupNotFoundResponse(
                    message="Block does not belong to this parallel group.",
                )

            # A parallel group needs at least two blocks; dissolve it if only
            # one remains.
            if len(dao.get_blocks(group_id)) < 2:
                dao.delete_group(group_id)

            db_session.commit()

        return JsonResponse(
            SuccessResponse(
                message="Parallel group member removed successfully",
                data=None,
            ).model_dump(),
        )
