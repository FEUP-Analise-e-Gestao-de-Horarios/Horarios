from enum import StrEnum

from django.http import JsonResponse


class ApiError(StrEnum):
    # Projects
    PROJECTS_CREATE_DUPLICATED_NAME = "projects.create.duplicated_name"
    PROJECTS_CREATE_FAILED = "projects.create.failed"
    PROJECTS_NOT_FOUND = "projects.not_found"
    PROJECTS_RENAME_DUPLICATED_NAME = "projects.rename.duplicated_name"
    PROJECTS_ROOMS_NOT_FOUND = "projects.rooms.not_found"
    PROJECTS_TEACHERS_NOT_FOUND = "projects.teachers.not_found"
    PROJECTS_DEGREES_NOT_FOUND = "projects.degrees.not_found"
    PROJECTS_YEARS_NOT_FOUND = "projects.years.not_found"

    # Auth
    AUTH_NOT_AUTHENTICATED = "auth.not_authenticated"
    AUTH_ALREADY_AUTHENTICATED = "auth.already_authenticated"
    AUTH_BAD_CREDENTIALS = "auth.bad_credentials"
    AUTH_INVALID_OLD_PASSWORD = "auth.invalid_old_password"
    AUTH_PASSWORD_POLICY_VIOLATION = "auth.password_policy_violation"

    # Generic
    INVALID_JSON = "generic.invalid_json"
    INVALID_BODY = "generic.invalid_body"


def ErrorResponse(*, status: int, code: ApiError, message: str) -> JsonResponse:
    return JsonResponse({"error": str(code), "message": message}, status=status)


def NotAuthenticatedResponse() -> JsonResponse:
    return ErrorResponse(
        status=401,
        code=ApiError.AUTH_NOT_AUTHENTICATED,
        message="User is not authenticated.",
    )


def ProjectNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_NOT_FOUND,
        message="Project not found.",
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


def YearNotFoundResponse() -> JsonResponse:
    return ErrorResponse(
        status=404,
        code=ApiError.PROJECTS_YEARS_NOT_FOUND,
        message="Year not found.",
    )
