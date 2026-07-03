"""Pure unit tests for core error helpers and the parallel-blocks schemas.

No database, no HTTP: these exercise ``src.core.errors`` (the ``ApiError`` enum,
the ``ErrorResponse`` builder and the parallel-blocks error helpers), the
``SuccessResponse`` envelope from ``src.core.schemas`` and the view/DAO Pydantic
schemas for parallel blocks (serialization, ``from_attributes`` mapping and the
required-vs-default ``confirmed_group_id`` asymmetry).

The error helpers return a ``django.http.JsonResponse``; assertions read
``status_code`` and ``json.loads(response.content)`` off it. ``SuccessResponse``
and the schemas keep NATIVE types in ``model_dump()`` (UUID/date/datetime
objects, nested models -> dicts); the wire form is produced by Django's
``DjangoJSONEncoder``, which is what the JSON-safety assertions use.
"""

import datetime
import json
import uuid

import pytest
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from pydantic import ValidationError

from src.core.errors import (
    AlreadyAuthenticatedResponse,
    ApiError,
    BadCredentialsResponse,
    ClassNotFoundResponse,
    DegreeNotFoundResponse,
    ErrorResponse,
    InvalidBodyResponse,
    InvalidJsonResponse,
    InvalidOldPasswordResponse,
    NotAuthenticatedResponse,
    ParallelGroupInvalidCandidatesResponse,
    PasswordPolicyViolationResponse,
    ProjectCreateDuplicatedNameResponse,
    ProjectCreateFailedResponse,
    ProjectNotFoundResponse,
    ProjectRenameDuplicatedNameResponse,
    RoomNotFoundResponse,
    SubjectNotFoundResponse,
    TeacherNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.projects_db.schemas.parallel_candidates import (
    ParallelBlockCandidateClass,
    ParallelBlockCandidateDegree,
    ParallelBlockCandidateEdge,
    ParallelBlockCandidateGroup,
    ParallelBlockCandidateNode,
    ParallelBlockCandidateSession,
    ParallelBlockCandidateSubject,
    ParallelBlockCandidateYear,
)
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.parallel_blocks import (
    ParallelCandidateGroupResponse,
    ParallelCandidateNode,
    ParallelGroupResponse,
)


# --------------------------------------------------------------------------- #
# Local helpers                                                               #
# --------------------------------------------------------------------------- #
def _decode(response: JsonResponse) -> dict[str, object]:
    """Return the decoded JSON body of a ``JsonResponse``."""
    return json.loads(response.content)


def _make_dao_group(
    *,
    confirmed_group_id: uuid.UUID | None = None,
    weekday: WeekDay = WeekDay.MONDAY,
) -> ParallelBlockCandidateGroup:
    """Build a fully-populated DAO ``ParallelBlockCandidateGroup``.

    One subject (one year owned by one degree), one node (a session with one
    class) and one edge between two block ids. ``confirmed_group_id`` is applied
    to the single node so callers can exercise both the ``None`` default and a
    concrete value.
    """
    degree = ParallelBlockCandidateDegree(
        id=uuid.uuid7(),
        acronym="LEI",
        name="Licenciatura em Engenharia Informática",
    )
    year = ParallelBlockCandidateYear(id=uuid.uuid7(), degree=degree)
    subject = ParallelBlockCandidateSubject(
        id=uuid.uuid7(),
        acronym="PROG",
        name="Programação",
        years=[year],
    )

    block_a = uuid.uuid7()
    block_b = uuid.uuid7()

    klass = ParallelBlockCandidateClass(id=uuid.uuid7(), code="C1", year_id=year.id)
    session = ParallelBlockCandidateSession(type="T", start_time=9, duration=2)
    node = ParallelBlockCandidateNode(
        original_block_id=block_a,
        confirmed_group_id=confirmed_group_id,
        first_week=datetime.date(2025, 9, 15),
        last_week=datetime.date(2025, 12, 1),
        session=session,
        classes=[klass],
    )
    edge = ParallelBlockCandidateEdge(
        source=block_a,
        target=block_b,
        weeks=[datetime.date(2025, 9, 15)],
    )
    return ParallelBlockCandidateGroup(
        candidate_group_id=uuid.uuid7(),
        weekday=weekday,
        subject=subject,
        nodes=[node],
        edges=[edge],
    )


def _candidate_response_dict(weekday: object) -> dict[str, object]:
    """A raw dict that validates as ``ParallelCandidateGroupResponse``.

    ``weekday`` is left as-passed so callers can feed PT/EN aliases. Nodes carry
    an explicit ``confirmed_group_id`` (required on the view schema).
    """
    year_id = uuid.uuid7()
    return {
        "candidate_group_id": uuid.uuid7(),
        "weekday": weekday,
        "subject": {
            "id": uuid.uuid7(),
            "acronym": "PROG",
            "name": "Programação",
            "years": [
                {
                    "id": year_id,
                    "degree": {"id": uuid.uuid7(), "acronym": "LEI", "name": "Lic"},
                },
            ],
        },
        "nodes": [
            {
                "original_block_id": uuid.uuid7(),
                "confirmed_group_id": None,
                "first_week": datetime.date(2025, 9, 15),
                "last_week": datetime.date(2025, 12, 1),
                "session": {"type": "T", "start_time": 9, "duration": 2},
                "classes": [{"id": uuid.uuid7(), "code": "C1", "year_id": year_id}],
            },
        ],
        "edges": [],
    }


# --------------------------------------------------------------------------- #
# ErrorResponse / error helpers / ApiError                                    #
# --------------------------------------------------------------------------- #
def test_error_response_builds_jsonresponse_with_str_code_and_status() -> None:
    """``ErrorResponse`` sets the HTTP status and a ``{error, message}`` body."""
    response = ErrorResponse(status=418, code=ApiError.INVALID_BODY, message="x")

    assert isinstance(response, JsonResponse)
    assert response.status_code == 418
    assert _decode(response) == {"error": "generic.invalid_body", "message": "x"}


_ERROR_HELPER_CASES = [
    pytest.param(
        InvalidBodyResponse("bad shape"),
        400,
        "generic.invalid_body",
        "bad shape",
        id="invalid_body_custom",
    ),
    pytest.param(
        InvalidJsonResponse(),
        400,
        "generic.invalid_json",
        "Invalid JSON.",
        id="invalid_json",
    ),
    pytest.param(
        NotAuthenticatedResponse(),
        401,
        "auth.not_authenticated",
        "User is not authenticated.",
        id="not_authenticated",
    ),
    pytest.param(
        ProjectNotFoundResponse(),
        404,
        "projects.not_found",
        "Project not found.",
        id="project_not_found",
    ),
    pytest.param(
        ParallelGroupInvalidCandidatesResponse(),
        400,
        "projects.parallel_groups.invalid_candidates",
        "Some classes are not parallel candidates.",
        id="parallel_invalid_default",
    ),
    pytest.param(
        ParallelGroupInvalidCandidatesResponse("blocks 1,2 not adjacent"),
        400,
        "projects.parallel_groups.invalid_candidates",
        "blocks 1,2 not adjacent",
        id="parallel_invalid_custom",
    ),
    # -- Auth builders (fixed messages) --------------------------------
    pytest.param(
        AlreadyAuthenticatedResponse(),
        400,
        "auth.already_authenticated",
        "Already authenticated.",
        id="already_authenticated",
    ),
    pytest.param(
        BadCredentialsResponse(),
        401,
        "auth.bad_credentials",
        "Invalid username or password.",
        id="bad_credentials",
    ),
    pytest.param(
        InvalidOldPasswordResponse(),
        401,
        "auth.invalid_old_password",
        "Incorrect old password.",
        id="invalid_old_password",
    ),
    pytest.param(
        PasswordPolicyViolationResponse("too short"),
        400,
        "auth.password_policy_violation",
        "too short",
        id="password_policy_custom_message",
    ),
    # -- Project builders (name interpolation + the sole 500) ----------
    pytest.param(
        ProjectCreateDuplicatedNameResponse("Foo"),
        400,
        "projects.create.duplicated_name",
        "A project with the name 'Foo' already exists.",
        id="project_create_duplicated_name_interpolated",
    ),
    pytest.param(
        ProjectRenameDuplicatedNameResponse("Bar"),
        400,
        "projects.rename.duplicated_name",
        "A project with the name 'Bar' already exists.",
        id="project_rename_duplicated_name_interpolated",
    ),
    pytest.param(
        ProjectCreateFailedResponse(),
        500,
        "projects.create.failed",
        "Failed to create project.",
        id="project_create_failed_500",
    ),
    # -- Entity not-found: 404 with a fixed message --------------------
    pytest.param(
        RoomNotFoundResponse(),
        404,
        "projects.rooms.not_found",
        "Room not found.",
        id="room_not_found",
    ),
    pytest.param(
        TeacherNotFoundResponse(),
        404,
        "projects.teachers.not_found",
        "Teacher not found.",
        id="teacher_not_found",
    ),
    pytest.param(
        DegreeNotFoundResponse(),
        404,
        "projects.degrees.not_found",
        "Degree not found.",
        id="degree_not_found",
    ),
    # -- Entity not-found: 404 with a default AND an overridable message
    pytest.param(
        YearNotFoundResponse(),
        404,
        "projects.years.not_found",
        "Year not found.",
        id="year_not_found_default",
    ),
    pytest.param(
        YearNotFoundResponse("Year 7 not found."),
        404,
        "projects.years.not_found",
        "Year 7 not found.",
        id="year_not_found_custom",
    ),
    pytest.param(
        SubjectNotFoundResponse(),
        404,
        "projects.subjects.not_found",
        "Subject not found.",
        id="subject_not_found_default",
    ),
    pytest.param(
        SubjectNotFoundResponse("No such subject."),
        404,
        "projects.subjects.not_found",
        "No such subject.",
        id="subject_not_found_custom",
    ),
    pytest.param(
        ClassNotFoundResponse(),
        404,
        "projects.classes.not_found",
        "Class not found.",
        id="class_not_found_default",
    ),
    pytest.param(
        ClassNotFoundResponse("Class A1 not found."),
        404,
        "projects.classes.not_found",
        "Class A1 not found.",
        id="class_not_found_custom",
    ),
]


@pytest.mark.parametrize(("response", "status", "code", "message"), _ERROR_HELPER_CASES)
def test_error_helper_status_code_message(
    response: JsonResponse,
    status: int,
    code: str,
    message: str,
) -> None:
    """Every error helper returns the exact status/code/message it promises."""
    assert response.status_code == status
    assert _decode(response) == {"error": code, "message": message}


# Every ``ApiError`` member paired with its expected wire string. A separate
# test asserts this list covers the whole enum, so a new member added without a
# case here fails loudly instead of going silently unverified.
_API_ERROR_WIRE_CASES = [
    (ApiError.INVALID_JSON, "generic.invalid_json"),
    (ApiError.INVALID_BODY, "generic.invalid_body"),
    (ApiError.AUTH_NOT_AUTHENTICATED, "auth.not_authenticated"),
    (ApiError.AUTH_ALREADY_AUTHENTICATED, "auth.already_authenticated"),
    (ApiError.AUTH_BAD_CREDENTIALS, "auth.bad_credentials"),
    (ApiError.AUTH_INVALID_OLD_PASSWORD, "auth.invalid_old_password"),
    (ApiError.AUTH_PASSWORD_POLICY_VIOLATION, "auth.password_policy_violation"),
    (ApiError.PROJECTS_CREATE_DUPLICATED_NAME, "projects.create.duplicated_name"),
    (ApiError.PROJECTS_CREATE_FAILED, "projects.create.failed"),
    (ApiError.PROJECTS_NOT_FOUND, "projects.not_found"),
    (ApiError.PROJECTS_RENAME_DUPLICATED_NAME, "projects.rename.duplicated_name"),
    (ApiError.PROJECTS_ROOMS_NOT_FOUND, "projects.rooms.not_found"),
    (ApiError.PROJECTS_TEACHERS_NOT_FOUND, "projects.teachers.not_found"),
    (ApiError.PROJECTS_DEGREES_NOT_FOUND, "projects.degrees.not_found"),
    (ApiError.PROJECTS_YEARS_NOT_FOUND, "projects.years.not_found"),
    (ApiError.PROJECTS_SUBJECTS_NOT_FOUND, "projects.subjects.not_found"),
    (ApiError.PROJECTS_CLASSES_NOT_FOUND, "projects.classes.not_found"),
    (
        ApiError.PROJECTS_PARALLEL_GROUPS_INVALID_CANDIDATES,
        "projects.parallel_groups.invalid_candidates",
    ),
    (
        ApiError.PROJECTS_PARALLEL_GROUPS_NOT_FOUND,
        "projects.parallel_groups.not_found",
    ),
]


@pytest.mark.parametrize(("member", "wire"), _API_ERROR_WIRE_CASES)
def test_api_error_values_are_exact_wire_strings(member: ApiError, wire: str) -> None:
    """``str()`` of each ``ApiError`` member yields its wire string."""
    assert str(member) == wire
    assert member.value == wire


def test_api_error_wire_string_cases_cover_every_member() -> None:
    """The wire-string cases enumerate the whole enum, so none drifts uncovered."""
    covered = {member for member, _ in _API_ERROR_WIRE_CASES}
    assert covered == set(ApiError)


# --------------------------------------------------------------------------- #
# SuccessResponse                                                             #
# --------------------------------------------------------------------------- #
def test_success_response_model_dump_exposes_native_fields() -> None:
    """``model_dump`` yields ``{timestamp, message, data}`` with native ``data``."""
    dumped = SuccessResponse(message="ok", data=5).model_dump()

    assert set(dumped.keys()) == {"timestamp", "message", "data"}
    assert dumped["message"] == "ok"
    assert dumped["data"] == 5
    assert isinstance(dumped["data"], int)
    assert isinstance(dumped["timestamp"], datetime.datetime)


def test_success_response_timestamp_defaults_to_recent_naive_datetime() -> None:
    """The default ``timestamp`` is a naive ``datetime.now()`` within bounds."""
    before = datetime.datetime.now()
    dumped = SuccessResponse(message="ok", data=None).model_dump()
    after = datetime.datetime.now()

    timestamp = dumped["timestamp"]
    assert isinstance(timestamp, datetime.datetime)
    assert timestamp.tzinfo is None
    assert before <= timestamp <= after


def test_success_response_list_of_models_dumps_to_dicts_with_native_ids() -> None:
    """A list of models becomes a list of dicts; nested UUIDs stay ``UUID``."""
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    group_id = uuid.uuid7()

    dumped = SuccessResponse(
        message="ok",
        data=[ParallelGroupResponse(group_id=group_id, block_ids=[block_a, block_b])],
    ).model_dump()

    entry = dumped["data"][0]
    assert isinstance(entry, dict)
    assert entry["group_id"] == group_id
    assert entry["block_ids"] == [block_a, block_b]
    assert all(isinstance(block, uuid.UUID) for block in entry["block_ids"])


def test_success_response_single_nested_model_dumps_to_dict() -> None:
    """A single (non-list) nested model in ``data`` dumps to a dict with native ids."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()

    dumped = SuccessResponse(
        message="ok",
        data=ParallelGroupResponse(group_id=group_id, block_ids=[block_a, block_b]),
    ).model_dump()

    assert isinstance(dumped["data"], dict)
    assert dumped["data"]["group_id"] == group_id
    assert dumped["data"]["block_ids"] == [block_a, block_b]


def test_success_response_dump_is_django_json_serializable() -> None:
    """A dump wrapping a candidate group survives ``DjangoJSONEncoder``.

    UUID -> str, date -> ``YYYY-MM-DD``, datetime -> ISO, WeekDay -> lowercase.
    """
    group = _make_dao_group()
    response = ParallelCandidateGroupResponse.model_validate(group)
    dumped = SuccessResponse(message="ok", data=[response]).model_dump()

    encoded = json.loads(json.dumps(dumped, cls=DjangoJSONEncoder))

    # timestamp -> ISO 8601 string (round-trips through fromisoformat).
    assert isinstance(encoded["timestamp"], str)
    datetime.datetime.fromisoformat(encoded["timestamp"])

    entry = encoded["data"][0]
    assert entry["weekday"] == "monday"
    # UUID -> str
    uuid.UUID(entry["candidate_group_id"])
    node = entry["nodes"][0]
    # date -> YYYY-MM-DD
    assert node["first_week"] == "2025-09-15"
    assert node["last_week"] == "2025-12-01"
    uuid.UUID(node["original_block_id"])


# --------------------------------------------------------------------------- #
# ParallelGroupResponse                                                       #
# --------------------------------------------------------------------------- #
def test_parallel_group_response_round_trips_group_id_and_block_ids() -> None:
    """Dumping then re-validating preserves ``group_id`` and block order."""
    group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()

    original = ParallelGroupResponse(group_id=group_id, block_ids=[block_a, block_b])
    dumped = original.model_dump()

    assert isinstance(dumped["group_id"], uuid.UUID)
    assert all(isinstance(block, uuid.UUID) for block in dumped["block_ids"])

    reparsed = ParallelGroupResponse.model_validate(dumped)
    assert reparsed.group_id == group_id
    assert reparsed.block_ids == [block_a, block_b]


# --------------------------------------------------------------------------- #
# ParallelCandidateGroupResponse from_attributes                             #
# --------------------------------------------------------------------------- #
def test_candidate_group_response_maps_from_dao_group_via_from_attributes() -> None:
    """A fully-populated DAO group validates by attribute name across the tree."""
    group = _make_dao_group()

    response = ParallelCandidateGroupResponse.model_validate(group)

    assert response.candidate_group_id == group.candidate_group_id
    assert response.weekday == WeekDay.MONDAY
    assert response.subject.id == group.subject.id
    assert response.subject.years[0].degree.acronym == "LEI"

    node = response.nodes[0]
    assert node.original_block_id == group.nodes[0].original_block_id
    assert node.confirmed_group_id is None
    assert node.session.type == "T"
    assert node.classes[0].year_id == group.subject.years[0].id

    edge = response.edges[0]
    assert edge.source == group.edges[0].source
    assert edge.target == group.edges[0].target
    assert edge.weeks == [datetime.date(2025, 9, 15)]


def test_candidate_group_response_surfaces_non_null_confirmed_group_id() -> None:
    """A DAO node's non-null ``confirmed_group_id`` flows through to the view schema."""
    confirmed = uuid.uuid7()
    group = _make_dao_group(confirmed_group_id=confirmed)

    response = ParallelCandidateGroupResponse.model_validate(group)

    assert response.nodes[0].confirmed_group_id == confirmed


def test_view_candidate_node_requires_confirmed_group_id_on_dict() -> None:
    """The view node makes ``confirmed_group_id`` required; the DAO node defaults it.

    ``model_validate`` on a raw dict omitting the field raises on the view schema,
    while the DAO schema accepts the omission (defaulting to ``None``).
    """
    year_id = uuid.uuid7()
    payload = {
        "original_block_id": uuid.uuid7(),
        "first_week": datetime.date(2025, 9, 15),
        "last_week": datetime.date(2025, 12, 1),
        "session": {"type": "T", "start_time": 9, "duration": 2},
        "classes": [{"id": uuid.uuid7(), "code": "C1", "year_id": year_id}],
    }

    with pytest.raises(ValidationError) as excinfo:
        ParallelCandidateNode.model_validate(payload)

    errors = excinfo.value.errors()
    assert any(
        error["type"] == "missing" and error["loc"] == ("confirmed_group_id",) for error in errors
    )

    # The DAO node defaults the field and validates fine on the same omission.
    dao_node = ParallelBlockCandidateNode.model_validate(payload)
    assert dao_node.confirmed_group_id is None


# --------------------------------------------------------------------------- #
# Weekday coercion / serialization                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("terça", WeekDay.TUESDAY),
        ("SATURDAY", WeekDay.SATURDAY),
    ],
)
def test_candidate_group_response_coerces_weekday_aliases(
    raw: str,
    expected: WeekDay,
) -> None:
    """PT/EN weekday aliases coerce to the canonical ``WeekDay`` member."""
    response = ParallelCandidateGroupResponse.model_validate(_candidate_response_dict(raw))
    assert response.weekday == expected


def test_candidate_group_response_rejects_unknown_weekday() -> None:
    """``domingo`` (Sunday) has no ``WeekDay`` member and is rejected."""
    with pytest.raises(ValidationError):
        ParallelCandidateGroupResponse.model_validate(_candidate_response_dict("domingo"))


def test_candidate_group_response_dump_keeps_weekday_value_and_is_json_safe() -> None:
    """The dumped weekday equals its lowercase value and serializes cleanly."""
    response = ParallelCandidateGroupResponse.model_validate(_candidate_response_dict("terça"))
    dumped = response.model_dump()

    # StrEnum compares equal to its lowercase string value.
    assert dumped["weekday"] == "tuesday"

    encoded = json.loads(json.dumps(dumped, cls=DjangoJSONEncoder))
    assert encoded["weekday"] == "tuesday"
