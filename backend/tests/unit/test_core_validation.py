"""Pure unit tests for ``src.core.validation`` and the parallel-blocks
request schemas.

These tests import the validation helpers directly and drive them with
throwaway pydantic models and raw bytes / ``QueryDict``s. No database and no
HTTP layer are involved. The error responses are ``JsonResponse`` objects, so
we read ``resp.status_code`` and ``json.loads(resp.content)``.
"""

import json
import uuid
from uuid import UUID

import pytest
from django.http import QueryDict
from pydantic import BaseModel, model_validator

from src.core.validation import (
    _format_validation_error,
    _query_params_to_dict,
    validate_query_params,
    validate_request_body,
)
from src.projects.views.schemas.parallel_blocks import (
    ConfirmAllRequest,
    ConfirmSubjectRequest,
    CreateParallelGroupRequest,
)


# A throwaway nested-list schema, used only to exercise the generic validation
# helper's dotted-loc formatting for list indices (e.g. ``groups.0.block_ids.0``).
# It deliberately mirrors a ``{"groups": [{candidate_group_id, block_ids}]}`` shape
# so the helper's list-index path building is covered independently of any
# production schema.
class _GroupEntry(BaseModel):
    candidate_group_id: UUID
    block_ids: list[UUID]


class _SaveRequest(BaseModel):
    groups: list[_GroupEntry]


def _error_payload(response) -> dict:
    """Decode a ``JsonResponse`` error envelope into a plain dict."""
    return json.loads(response.content)


# --------------------------------------------------------------------------
# validate_request_body: happy path
# --------------------------------------------------------------------------
def test_validate_request_body_empty_groups_returns_model() -> None:
    """A valid body with no groups parses to a model and no error response."""
    model, error = validate_request_body(_SaveRequest, b'{"groups": []}')

    assert error is None
    assert isinstance(model, _SaveRequest)
    assert model.groups == []


def test_validate_request_body_one_entry_returns_model() -> None:
    """A single well-formed entry parses into a nested entry model."""
    candidate_group_id = uuid.uuid7()
    block_id = uuid.uuid7()
    body = json.dumps(
        {"groups": [{"candidate_group_id": str(candidate_group_id), "block_ids": [str(block_id)]}]},
    ).encode()

    model, error = validate_request_body(_SaveRequest, body)

    assert error is None
    assert isinstance(model, _SaveRequest)
    assert len(model.groups) == 1
    entry = model.groups[0]
    assert entry.candidate_group_id == candidate_group_id
    assert entry.block_ids == [block_id]


# --------------------------------------------------------------------------
# validate_request_body: malformed JSON funnels through the ValidationError
# branch, so the code is generic.invalid_body (NOT generic.invalid_json).
# --------------------------------------------------------------------------
@pytest.mark.parametrize("body", [b"{not json", b""])
def test_validate_request_body_malformed_json(body: bytes) -> None:
    """Malformed / empty JSON yields a 400 invalid_body response mentioning JSON."""
    model, error = validate_request_body(_SaveRequest, body)

    assert model is None
    assert error is not None
    assert error.status_code == 400

    payload = _error_payload(error)
    assert payload["error"] == "generic.invalid_body"
    assert payload["error"] != "generic.invalid_json"
    assert "Invalid JSON" in payload["message"]


# --------------------------------------------------------------------------
# validate_request_body + _format_validation_error: field-level formatting
# --------------------------------------------------------------------------
def test_validate_request_body_single_missing_field() -> None:
    """A missing top-level field is prefixed with its dotted loc."""
    model, error = validate_request_body(_SaveRequest, b"{}")

    assert model is None
    assert error is not None
    assert error.status_code == 400

    payload = _error_payload(error)
    assert payload["error"] == "generic.invalid_body"
    assert payload["message"].startswith("groups:")
    assert "Field required" in payload["message"]


def test_validate_request_body_joins_multiple_errors() -> None:
    """Multiple errors are joined with '; ' and each carries its dotted loc."""
    body = json.dumps(
        {"groups": [{"candidate_group_id": "not-a-uuid", "block_ids": ["also-bad"]}]},
    ).encode()

    model, error = validate_request_body(_SaveRequest, body)

    assert model is None
    assert error is not None
    payload = _error_payload(error)
    message = payload["message"]

    assert "; " in message
    assert "groups.0.candidate_group_id:" in message
    assert "groups.0.block_ids.0:" in message


def test_validate_request_body_dotted_loc_for_nested_index() -> None:
    """A nested missing field builds the full dotted path with the list index."""
    body = json.dumps({"groups": [{"block_ids": []}]}).encode()

    model, error = validate_request_body(_SaveRequest, body)

    assert model is None
    assert error is not None
    payload = _error_payload(error)
    assert payload["message"] == "groups.0.candidate_group_id: Field required"


# --------------------------------------------------------------------------
# _format_validation_error: bare-msg fallback when loc is empty
# --------------------------------------------------------------------------
def test_format_validation_error_empty_loc_falls_back_to_bare_msg() -> None:
    """A root ``model_validator`` error has empty loc, so no dotted prefix."""

    class _RaisingModel(BaseModel):
        @model_validator(mode="after")
        def _always_fail(self) -> _RaisingModel:
            raise ValueError("boom")

    try:
        _RaisingModel.model_validate({})
    except Exception as exc:
        errors = exc.errors()
        assert errors[0]["loc"] == ()
        formatted = _format_validation_error(exc)
    else:  # pragma: no cover - the validator always raises
        pytest.fail("expected a ValidationError")

    assert formatted == "Value error, boom"
    assert not formatted.startswith(":")
    assert not formatted.startswith(" ")


# --------------------------------------------------------------------------
# validate_query_params + _query_params_to_dict
# --------------------------------------------------------------------------
def test_validate_query_params_defaults_with_empty_querydict() -> None:
    """Absent params fall back to the model defaults; no error is returned."""

    class _Model(BaseModel):
        a: str = "def"
        tags: list[str] = []

    model, error = validate_query_params(_Model, QueryDict(""))

    assert error is None
    assert isinstance(model, _Model)
    assert model.a == "def"
    assert model.tags == []


def test_query_params_to_dict_getlist_for_lists_last_wins_for_scalars() -> None:
    """List fields collect every value; scalar fields keep the last value."""

    class _Model(BaseModel):
        ids: list[UUID]
        name: str

    id_a = "00000000-0000-0000-0000-000000000001"
    id_b = "00000000-0000-0000-0000-000000000002"
    query = QueryDict(f"ids={id_a}&ids={id_b}&name=a&name=b")

    result = _query_params_to_dict(_Model, query)

    assert result == {"ids": [id_a, id_b], "name": "b"}


def test_query_params_to_dict_only_emits_present_keys() -> None:
    """Keys absent from the ``QueryDict`` are not emitted at all."""

    class _Model(BaseModel):
        ids: list[UUID]
        name: str

    result = _query_params_to_dict(_Model, QueryDict("name=a"))

    assert result == {"name": "a"}


def test_validate_query_params_missing_required_param() -> None:
    """A required param absent from the query yields a 400 invalid_body."""

    class _Model(BaseModel):
        ids: list[UUID]
        name: str

    model, error = validate_query_params(_Model, QueryDict("name=a"))

    assert model is None
    assert error is not None
    assert error.status_code == 400
    payload = _error_payload(error)
    assert payload["error"] == "generic.invalid_body"
    assert payload["message"] == "ids: Field required"


def test_validate_query_params_unparseable_scalar() -> None:
    """A scalar that cannot coerce to the field type is prefixed with its loc."""

    class _Model(BaseModel):
        n: int

    model, error = validate_query_params(_Model, QueryDict("n=abc"))

    assert model is None
    assert error is not None
    assert error.status_code == 400
    payload = _error_payload(error)
    assert payload["message"].startswith("n:")


# --------------------------------------------------------------------------
# CreateParallelGroupRequest schema behavior
# --------------------------------------------------------------------------
def test_create_request_round_trips_from_json() -> None:
    """A create request survives a JSON -> model -> JSON round-trip."""
    candidate_group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    raw = json.dumps(
        {
            "candidate_group_id": str(candidate_group_id),
            "block_ids": [str(block_a), str(block_b)],
        },
    )

    model = CreateParallelGroupRequest.model_validate_json(raw)

    assert isinstance(model.candidate_group_id, UUID)
    assert model.candidate_group_id == candidate_group_id
    assert model.block_ids == [block_a, block_b]
    assert all(isinstance(block_id, UUID) for block_id in model.block_ids)

    redumped = model.model_dump_json()
    assert CreateParallelGroupRequest.model_validate_json(redumped) == model


@pytest.mark.parametrize("kind", ["empty", "duplicate"])
def test_create_request_allows_empty_and_duplicate_block_ids(kind: str) -> None:
    """The schema imposes no min-length or uniqueness constraint on block_ids."""
    candidate_group_id = uuid.uuid7()
    dup = uuid.uuid7()
    block_ids = [] if kind == "empty" else [dup, dup]

    model = CreateParallelGroupRequest(candidate_group_id=candidate_group_id, block_ids=block_ids)

    assert model.block_ids == block_ids


@pytest.mark.parametrize("missing", ["candidate_group_id", "block_ids"])
def test_create_request_requires_both_fields(missing: str) -> None:
    """Omitting a required field raises a ValidationError located at that field."""
    payload: dict = {
        "candidate_group_id": str(uuid.uuid7()),
        "block_ids": [str(uuid.uuid7())],
    }
    del payload[missing]

    with pytest.raises(Exception) as exc_info:
        CreateParallelGroupRequest.model_validate(payload)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == (missing,)
    assert errors[0]["type"] == "missing"


@pytest.mark.parametrize(
    ("payload", "expected_loc"),
    [
        (
            {"candidate_group_id": "xyz", "block_ids": []},
            ("candidate_group_id",),
        ),
        (
            {"candidate_group_id": str(uuid.uuid7()), "block_ids": ["not-a-uuid"]},
            ("block_ids", 0),
        ),
    ],
)
def test_create_request_rejects_non_uuid_fields(payload: dict, expected_loc: tuple) -> None:
    """Non-UUID values raise a ValidationError with the offending field's loc."""
    with pytest.raises(Exception) as exc_info:
        CreateParallelGroupRequest.model_validate(payload)

    locs = [err["loc"] for err in exc_info.value.errors()]
    assert expected_loc in locs


def test_create_request_ignores_unknown_fields() -> None:
    """Unknown keys are dropped, not rejected (the schema does not forbid extras)."""
    model = CreateParallelGroupRequest.model_validate(
        {
            "candidate_group_id": str(uuid.uuid7()),
            "block_ids": [str(uuid.uuid7())],
            "bogus": 1,
        },
    )

    assert not hasattr(model, "bogus")


# --------------------------------------------------------------------------
# ConfirmSubjectRequest schema behavior
# --------------------------------------------------------------------------
def test_confirm_subject_request_round_trips_from_json() -> None:
    """A confirm-subject request survives a JSON -> model -> JSON round-trip."""
    subject_id = uuid.uuid7()
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    raw = json.dumps(
        {
            "subject_id": str(subject_id),
            "candidate_group_ids": [str(c1), str(c2)],
        },
    )

    model = ConfirmSubjectRequest.model_validate_json(raw)

    assert isinstance(model.subject_id, UUID)
    assert model.subject_id == subject_id
    assert model.candidate_group_ids == [c1, c2]
    assert all(isinstance(cid, UUID) for cid in model.candidate_group_ids)
    assert ConfirmSubjectRequest.model_validate_json(model.model_dump_json()) == model


def test_confirm_subject_request_allows_empty_candidate_ids() -> None:
    """An empty candidate list is accepted (an empty confirm has real semantics)."""
    model = ConfirmSubjectRequest(subject_id=uuid.uuid7(), candidate_group_ids=[])

    assert model.candidate_group_ids == []


@pytest.mark.parametrize("missing", ["subject_id", "candidate_group_ids"])
def test_confirm_subject_request_requires_both_fields(missing: str) -> None:
    """Omitting a required field raises a ValidationError located at that field."""
    payload: dict = {
        "subject_id": str(uuid.uuid7()),
        "candidate_group_ids": [str(uuid.uuid7())],
    }
    del payload[missing]

    with pytest.raises(Exception) as exc_info:
        ConfirmSubjectRequest.model_validate(payload)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == (missing,)
    assert errors[0]["type"] == "missing"


@pytest.mark.parametrize(
    ("payload", "expected_loc"),
    [
        (
            {"subject_id": "xyz", "candidate_group_ids": []},
            ("subject_id",),
        ),
        (
            {"subject_id": str(uuid.uuid7()), "candidate_group_ids": ["not-a-uuid"]},
            ("candidate_group_ids", 0),
        ),
    ],
)
def test_confirm_subject_request_rejects_non_uuid_fields(
    payload: dict,
    expected_loc: tuple,
) -> None:
    """Non-UUID values raise a ValidationError with the offending field's loc."""
    with pytest.raises(Exception) as exc_info:
        ConfirmSubjectRequest.model_validate(payload)

    locs = [err["loc"] for err in exc_info.value.errors()]
    assert expected_loc in locs


def test_confirm_subject_request_rejects_non_list_candidate_ids() -> None:
    """A scalar where a list is expected is a validation error, not a coercion."""
    with pytest.raises(Exception) as exc_info:
        ConfirmSubjectRequest.model_validate(
            {"subject_id": str(uuid.uuid7()), "candidate_group_ids": str(uuid.uuid7())},
        )

    assert exc_info.value.errors()[0]["loc"] == ("candidate_group_ids",)


# --------------------------------------------------------------------------
# ConfirmAllRequest schema behavior
# --------------------------------------------------------------------------
def test_confirm_all_request_round_trips_from_json() -> None:
    """A confirm-all request survives a JSON -> model -> JSON round-trip."""
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    raw = json.dumps({"candidate_group_ids": [str(c1), str(c2)]})

    model = ConfirmAllRequest.model_validate_json(raw)

    assert model.candidate_group_ids == [c1, c2]
    assert all(isinstance(cid, UUID) for cid in model.candidate_group_ids)
    assert ConfirmAllRequest.model_validate_json(model.model_dump_json()) == model


def test_confirm_all_request_allows_empty_candidate_ids() -> None:
    """An empty candidate list is accepted (confirm-all over an empty candidate set)."""
    model = ConfirmAllRequest(candidate_group_ids=[])

    assert model.candidate_group_ids == []


def test_confirm_all_request_requires_candidate_ids() -> None:
    """Omitting candidate_group_ids raises a ValidationError at that field."""
    with pytest.raises(Exception) as exc_info:
        ConfirmAllRequest.model_validate({})

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("candidate_group_ids",)
    assert errors[0]["type"] == "missing"


def test_confirm_all_request_rejects_non_uuid_element() -> None:
    """A non-UUID element is located at its list index."""
    with pytest.raises(Exception) as exc_info:
        ConfirmAllRequest.model_validate({"candidate_group_ids": ["not-a-uuid"]})

    assert ("candidate_group_ids", 0) in [err["loc"] for err in exc_info.value.errors()]


def test_confirm_all_request_rejects_non_list() -> None:
    """A scalar where a list is expected is rejected, not coerced."""
    with pytest.raises(Exception) as exc_info:
        ConfirmAllRequest.model_validate({"candidate_group_ids": str(uuid.uuid7())})

    assert exc_info.value.errors()[0]["loc"] == ("candidate_group_ids",)
