from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    InvalidBodyResponse,
    ParallelConfirmationStaleResponse,
    ParallelGroupInvalidCandidatesResponse,
    ParallelGroupNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_request_body
from src.projects.models import Project
from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_block_group_dao import ParallelBlockGroupDAO
from src.projects.projects_db.dao.parallel_confirmed_candidate_dao import (
    ParallelConfirmedCandidateDAO,
)
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.parallel_blocks import (
    ConfirmAllRequest,
    ConfirmedCandidatesResponse,
    ConfirmSubjectRequest,
    CreatedParallelGroupResponse,
    CreateParallelGroupRequest,
    ParallelCandidateGroupResponse,
    ParallelGroupResponse,
)


class ProjectParallelBlockCandidateView(View):
    """API endpoint: list parallel classes."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            parallel_block_candidate_dao = ParallelBlockCandidateDAO(db_session)

            groups = parallel_block_candidate_dao.get_all_groups_with_info()

            # get_all_groups_with_info reconciles the stored confirmations
            # against the fresh components, pruning stale ids; persist that.
            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Candidate parallel groups retrieved successfully",
                    data=[ParallelCandidateGroupResponse.model_validate(group) for group in groups],
                ).model_dump(),
            )


class ProjectParallelBlockGroupsView(View):
    """API endpoint: list, create, and clear confirmed parallel block groups."""

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

        validated, err = validate_request_body(CreateParallelGroupRequest, request.body)
        if err:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            components = {
                component.candidate_group_id: component
                for component in ParallelBlockCandidateDAO(db_session).get_candidate_components()
            }

            blocks = set(validated.block_ids)
            component = components.get(validated.candidate_group_id)
            if len(blocks) < 2 or component is None or not component.is_connected_subset(blocks):
                return ParallelGroupInvalidCandidatesResponse()

            dao = ParallelBlockGroupDAO(db_session)
            try:
                group_id = dao.create(validated.block_ids)
            except ValueError as exc:
                return InvalidBodyResponse(str(exc))

            db_session.commit()

            Project.objects.filter(pk=project_id).update(has_selected_parallel_sessions=True)

            return JsonResponse(
                SuccessResponse(
                    message="Parallel group created successfully",
                    data=CreatedParallelGroupResponse(group_id=group_id),
                ).model_dump(),
            )

    @require_auth
    @require_project
    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            dao = ParallelBlockGroupDAO(db_session)
            removed = dao.clear_all()

            db_session.commit()

            Project.objects.filter(pk=project_id).update(has_selected_parallel_sessions=True)

            return JsonResponse(
                SuccessResponse(
                    message="Parallel group members cleared successfully",
                    data=removed,
                ).model_dump(),
            )


class ProjectParallelBlockGroupView(View):
    """API endpoint: delete a single confirmed parallel block group."""

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


class ProjectParallelConfirmationsView(View):
    """API endpoint: confirm a subject's candidates, or clear all confirmations."""

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:

        validated, err = validate_request_body(ConfirmSubjectRequest, request.body)
        if err:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            candidate_dao = ParallelBlockCandidateDAO(db_session)
            confirmed_dao = ParallelConfirmedCandidateDAO(db_session)

            candidate_ids = candidate_dao.candidate_ids_for_subject(validated.subject_id)
            # Abort if the client's view of this subject's candidates is stale, so
            # a confirmation is never recorded against candidates that changed.
            if candidate_ids != set(validated.candidate_group_ids):
                return ParallelConfirmationStaleResponse()

            confirmed_dao.add(candidate_ids)

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Subject candidates confirmed successfully",
                    data=ConfirmedCandidatesResponse(candidate_group_ids=sorted(candidate_ids)),
                ).model_dump(),
            )

    @require_auth
    @require_project
    def delete(self, request: HttpRequest, project_id: int) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            confirmed_dao = ParallelConfirmedCandidateDAO(db_session)
            removed = confirmed_dao.clear_all()

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Confirmations cleared successfully",
                    data=removed,
                ).model_dump(),
            )


class ProjectParallelConfirmAllView(View):
    """API endpoint: confirm every current candidate across all subjects."""

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:

        validated, err = validate_request_body(ConfirmAllRequest, request.body)
        if err:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            candidate_dao = ParallelBlockCandidateDAO(db_session)
            confirmed_dao = ParallelConfirmedCandidateDAO(db_session)

            candidate_ids = candidate_dao.all_candidate_ids()
            # Abort if the client's view of the candidates is stale, so nothing is
            # confirmed against a set that changed under it.
            if candidate_ids != set(validated.candidate_group_ids):
                return ParallelConfirmationStaleResponse()

            confirmed_dao.add(candidate_ids)

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="All candidates confirmed successfully",
                    data=ConfirmedCandidatesResponse(candidate_group_ids=sorted(candidate_ids)),
                ).model_dump(),
            )


class ProjectParallelConfirmationView(View):
    """API endpoint: remove a single subject's confirmation."""

    @require_auth
    @require_project
    def delete(self, request: HttpRequest, project_id: int, subject_id: UUID) -> HttpResponse:

        with get_project_session(general_db(project_id)) as db_session:
            candidate_dao = ParallelBlockCandidateDAO(db_session)
            confirmed_dao = ParallelConfirmedCandidateDAO(db_session)

            candidate_ids = candidate_dao.candidate_ids_for_subject(subject_id)
            removed = confirmed_dao.remove(candidate_ids)

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Subject confirmation removed successfully",
                    data=removed,
                ).model_dump(),
            )
