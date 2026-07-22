from enum import StrEnum

from django.http import JsonResponse


class ApiError(StrEnum):
    # Generic
    INVALID_JSON = "generic.invalid_json"
    INVALID_BODY = "generic.invalid_body"

    # Auth
    AUTH_NOT_AUTHENTICATED = "auth.not_authenticated"
    AUTH_ALREADY_AUTHENTICATED = "auth.already_authenticated"
    AUTH_BAD_CREDENTIALS = "auth.bad_credentials"
    AUTH_INVALID_OLD_PASSWORD = "auth.invalid_old_password"
    AUTH_PASSWORD_POLICY_VIOLATION = "auth.password_policy_violation"

    # Projects
    PROJECTS_CREATE_DUPLICATED_NAME = "projects.create.duplicated_name"
    PROJECTS_CREATE_FAILED = "projects.create.failed"
    PROJECTS_NOT_FOUND = "projects.not_found"
    PROJECTS_RENAME_DUPLICATED_NAME = "projects.rename.duplicated_name"

    # Projects - Entities
    PROJECTS_ROOMS_NOT_FOUND = "projects.rooms.not_found"
    PROJECTS_TEACHERS_NOT_FOUND = "projects.teachers.not_found"
    PROJECTS_DEGREES_NOT_FOUND = "projects.degrees.not_found"
    PROJECTS_YEARS_NOT_FOUND = "projects.years.not_found"
    PROJECTS_SUBJECTS_NOT_FOUND = "projects.subjects.not_found"
    PROJECTS_CLASSES_NOT_FOUND = "projects.classes.not_found"
    PROJECTS_SESSIONS_NOT_FOUND = "projects.sessions.not_found"

    # Projects - Parallel groups
    PROJECTS_PARALLEL_GROUPS_INVALID_CANDIDATES = "projects.parallel_groups.invalid_candidates"
    PROJECTS_PARALLEL_GROUPS_NOT_FOUND = "projects.parallel_groups.not_found"
    PROJECTS_PARALLEL_CONFIRMATION_STALE = "projects.parallel_confirmation.stale"


def ErrorResponse(*, status: int, code: ApiError, message: str) -> JsonResponse:
    return JsonResponse({"error": str(code), "message": message}, status=status)


def InvalidJsonResponse() -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.INVALID_JSON,
        message="Invalid JSON.",
    )


def InvalidBodyResponse(message: str) -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.INVALID_BODY,
        message=message,
    )


def NotAuthenticatedResponse() -> JsonResponse:
    return ErrorResponse(
        status=401,
        code=ApiError.AUTH_NOT_AUTHENTICATED,
        message="User is not authenticated.",
    )


def AlreadyAuthenticatedResponse() -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.AUTH_ALREADY_AUTHENTICATED,
        message="Already authenticated.",
    )


def BadCredentialsResponse() -> JsonResponse:
    return ErrorResponse(
        status=401,
        code=ApiError.AUTH_BAD_CREDENTIALS,
        message="Invalid username or password.",
    )


def InvalidOldPasswordResponse() -> JsonResponse:
    return ErrorResponse(
        status=401,
        code=ApiError.AUTH_INVALID_OLD_PASSWORD,
        message="Incorrect old password.",
    )


def PasswordPolicyViolationResponse(message: str) -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.AUTH_PASSWORD_POLICY_VIOLATION,
        message=message,
    )


def ProjectCreateDuplicatedNameResponse(name: str) -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.PROJECTS_CREATE_DUPLICATED_NAME,
        message=f"A project with the name '{name}' already exists.",
    )


def ProjectCreateFailedResponse() -> JsonResponse:
    return ErrorResponse(
        status=500,
        code=ApiError.PROJECTS_CREATE_FAILED,
        message="Failed to create project.",
    )


def ProjectNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_NOT_FOUND,
        message="Project not found.",
    )


def ProjectRenameDuplicatedNameResponse(name: str) -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.PROJECTS_RENAME_DUPLICATED_NAME,
        message=f"A project with the name '{name}' already exists.",
    )


def RoomNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_ROOMS_NOT_FOUND,
        message="Room not found.",
    )


def TeacherNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_TEACHERS_NOT_FOUND,
        message="Teacher not found.",
    )


def DegreeNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_DEGREES_NOT_FOUND,
        message="Degree not found.",
    )


def YearNotFoundResponse(message: str = "Year not found.") -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_YEARS_NOT_FOUND,
        message=message,
    )


def SubjectNotFoundResponse(message: str = "Subject not found.") -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_SUBJECTS_NOT_FOUND,
        message=message,
    )


def ClassNotFoundResponse(message: str = "Class not found.") -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_CLASSES_NOT_FOUND,
        message=message,
    )


def SessionNotFoundResponse(message: str = "Session not found.") -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_SESSIONS_NOT_FOUND,
        message=message,
    )


def ParallelGroupInvalidCandidatesResponse(
    message: str = "Some classes are not parallel candidates.",
) -> JsonResponse:
    return ErrorResponse(
        status=400,
        code=ApiError.PROJECTS_PARALLEL_GROUPS_INVALID_CANDIDATES,
        message=message,
    )


def ParallelGroupNotFoundResponse(message: str = "Parallel group not found.") -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_PARALLEL_GROUPS_NOT_FOUND,
        message=message,
    )


def ParallelConfirmationStaleResponse(
    message: str = "The subject's candidates changed since the list was loaded.",
) -> JsonResponse:
    return ErrorResponse(
        status=409,
        code=ApiError.PROJECTS_PARALLEL_CONFIRMATION_STALE,
        message=message,
    )
