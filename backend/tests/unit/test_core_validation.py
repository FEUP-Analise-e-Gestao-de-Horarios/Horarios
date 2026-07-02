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
    ParallelGroupEntry,
    SaveParallelGroupMembersRequest,
)


def _error_payload(response) -> dict:
    """Decode a ``JsonResponse`` error envelope into a plain dict."""
    return json.loads(response.content)


# --------------------------------------------------------------------------
# validate_request_body: happy path
# --------------------------------------------------------------------------
def test_validate_request_body_empty_groups_returns_model() -> None:
    """A valid body with no groups parses to a model and no error response."""
    model, error = validate_request_body(SaveParallelGroupMembersRequest, b'{"groups": []}')

    assert error is None
    assert isinstance(model, SaveParallelGroupMembersRequest)
    assert model.groups == []


def test_validate_request_body_one_entry_returns_model() -> None:
    """A single well-formed entry parses into a ``ParallelGroupEntry``."""
    candidate_group_id = uuid.uuid7()
    block_id = uuid.uuid7()
    body = json.dumps(
        {"groups": [{"candidate_group_id": str(candidate_group_id), "block_ids": [str(block_id)]}]},
    ).encode()

    model, error = validate_request_body(SaveParallelGroupMembersRequest, body)

    assert error is None
    assert isinstance(model, SaveParallelGroupMembersRequest)
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
    model, error = validate_request_body(SaveParallelGroupMembersRequest, body)

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
    model, error = validate_request_body(SaveParallelGroupMembersRequest, b"{}")

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

    model, error = validate_request_body(SaveParallelGroupMembersRequest, body)

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

    model, error = validate_request_body(SaveParallelGroupMembersRequest, body)

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
# ParallelGroupEntry / SaveParallelGroupMembersRequest schema behavior
# --------------------------------------------------------------------------
def test_save_request_round_trips_from_json() -> None:
    """A one-entry request survives a JSON -> model -> JSON round-trip."""
    candidate_group_id = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    raw = json.dumps(
        {
            "groups": [
                {
                    "candidate_group_id": str(candidate_group_id),
                    "block_ids": [str(block_a), str(block_b)],
                },
            ],
        },
    )

    model = SaveParallelGroupMembersRequest.model_validate_json(raw)

    entry = model.groups[0]
    assert isinstance(entry.candidate_group_id, UUID)
    assert entry.candidate_group_id == candidate_group_id
    assert entry.block_ids == [block_a, block_b]
    assert all(isinstance(block_id, UUID) for block_id in entry.block_ids)

    redumped = model.model_dump_json()
    assert SaveParallelGroupMembersRequest.model_validate_json(redumped) == model


@pytest.mark.parametrize("kind", ["empty", "duplicate"])
def test_parallel_group_entry_allows_empty_and_duplicate_block_ids(kind: str) -> None:
    """The schema imposes no min-length or uniqueness constraint on block_ids."""
    candidate_group_id = uuid.uuid7()
    dup = uuid.uuid7()
    block_ids = [] if kind == "empty" else [dup, dup]

    entry = ParallelGroupEntry(candidate_group_id=candidate_group_id, block_ids=block_ids)

    assert entry.block_ids == block_ids


def test_save_request_requires_groups_key() -> None:
    """Omitting the ``groups`` key raises a ValidationError located at ('groups',)."""
    with pytest.raises(Exception) as exc_info:
        SaveParallelGroupMembersRequest.model_validate({})

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("groups",)
    assert errors[0]["type"] == "missing"


@pytest.mark.parametrize(
    ("payload", "expected_loc"),
    [
        (
            {"groups": [{"candidate_group_id": "xyz", "block_ids": []}]},
            ("groups", 0, "candidate_group_id"),
        ),
        (
            {"groups": [{"candidate_group_id": str(uuid.uuid7()), "block_ids": ["not-a-uuid"]}]},
            ("groups", 0, "block_ids", 0),
        ),
    ],
)
def test_save_request_rejects_non_uuid_fields(payload: dict, expected_loc: tuple) -> None:
    """Non-UUID values raise a ValidationError with the offending field's loc."""
    with pytest.raises(Exception) as exc_info:
        SaveParallelGroupMembersRequest.model_validate(payload)

    locs = [err["loc"] for err in exc_info.value.errors()]
    assert expected_loc in locs
