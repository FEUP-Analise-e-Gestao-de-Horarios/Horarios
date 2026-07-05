"""Unit tests for :mod:`src.exporter.schemas`.

The exporter's pydantic models double as its wire contract and its coercion
layer: ids/dates coerce to strings, optional strings preserve ``None``, the
snapshot/modification models accept extra keys, and the step ``type`` and
compact ``format`` are constrained literals. These tests pin that behavior.
"""

import datetime
import uuid

from pydantic import ValidationError
from pytest import mark, raises

from src.exporter.schemas import (
    CompactProjectExportPayload,
    ExportClassConflict,
    ExportColumnChange,
    ExportModificationStep,
    ExportRoomConflict,
    ExportRoomRelationChange,
    ExportSessionModifications,
    ExportSessionRecord,
    ExportSessionSnapshot,
    ExportSubjectSnapshot,
    ExportTeacherConflict,
    ExportTeacherRelationChange,
    ExportTeacherSnapshot,
    ProjectExportPayload,
)
from src.projects.projects_db.schemas.weekday import WeekDay

# ---------------------------------------------------------------------------
# -- String coercion validators
# ---------------------------------------------------------------------------


def test_export_string_coerces_uuid_and_int_to_str() -> None:
    session_uuid = uuid.uuid7()
    assert ExportSessionRecord(id=session_uuid).id == str(session_uuid)
    assert ExportSessionRecord(id=12345).id == "12345"


def test_export_optional_string_preserves_none_but_stringifies_values() -> None:
    change = ExportRoomRelationChange(room_id="r1")
    assert change.room_name is None

    populated = ExportRoomRelationChange(room_id=1, room_name="B101", room_seats=99)
    assert populated.room_id == "1"
    assert populated.room_name == "B101"
    # Non-string scalar is coerced to its string form.
    assert populated.room_seats == "99"


def test_teacher_relation_change_keeps_number_as_int() -> None:
    change = ExportTeacherRelationChange(teacher_id="t1", teacher_number=7)
    assert change.teacher_id == "t1"
    assert change.teacher_number == 7

    assert ExportTeacherRelationChange(teacher_id="t1").teacher_number is None


# ---------------------------------------------------------------------------
# -- ExportColumnChange
# ---------------------------------------------------------------------------


def test_column_change_accepts_arbitrary_json_values() -> None:
    change = ExportColumnChange(old=None, new={"nested": [1, 2, 3]})
    assert change.old is None
    assert change.new == {"nested": [1, 2, 3]}


def test_column_change_preserves_null_pair() -> None:
    dumped = ExportColumnChange(old=None, new=None).model_dump()
    assert dumped == {"old": None, "new": None}


# ---------------------------------------------------------------------------
# -- ExportSessionSnapshot
# ---------------------------------------------------------------------------


def test_session_snapshot_coerces_ids_and_dates_and_nests_children() -> None:
    snapshot = ExportSessionSnapshot.model_validate(
        {
            "id": uuid.UUID("019e21c0-8ed5-7722-bd5e-8ad5a3c750b3"),
            "start_time": 830,
            "duration": 2,
            "weekday": WeekDay.MONDAY,
            "week": datetime.date(2026, 1, 5),
            "rooms": ["B101"],
            "teachers": [{"number": 1, "name": "Ada", "acronym": "AA"}],
            "classes": ["1LEIC01"],
            "subjects": [{"name": "IA", "acronym": "IA", "code": "IA001"}],
        },
    )
    assert snapshot.id == "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3"
    assert snapshot.weekday == "monday"
    assert snapshot.week == "2026-01-05"
    assert snapshot.teachers[0].name == "Ada"
    assert snapshot.subjects[0].code == "IA001"


def test_session_snapshot_allows_and_preserves_extra_fields() -> None:
    snapshot = ExportSessionSnapshot.model_validate(
        {
            "id": "s1",
            "start_time": 830,
            "duration": 2,
            "weekday": "monday",
            "week": "2026-01-05",
            "custom_flag": True,
        },
    )
    assert snapshot.model_dump()["custom_flag"] is True


def test_session_snapshot_defaults_relation_lists_to_empty() -> None:
    snapshot = ExportSessionSnapshot(
        id="s1",
        start_time=830,
        duration=2,
        weekday="monday",
        week="2026-01-05",
    )
    assert snapshot.rooms == []
    assert snapshot.teachers == []
    assert snapshot.classes == []
    assert snapshot.subjects == []


@mark.parametrize("missing", ["id", "start_time", "duration", "weekday", "week"])
def test_session_snapshot_requires_core_fields(missing: str) -> None:
    data = {
        "id": "s1",
        "start_time": 830,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
    }
    del data[missing]
    with raises(ValidationError):
        ExportSessionSnapshot.model_validate(data)


def test_subject_snapshot_optional_acronym() -> None:
    subject = ExportSubjectSnapshot(name="IA", code="IA001")
    assert subject.acronym is None


def test_teacher_snapshot_requires_number() -> None:
    with raises(ValidationError):
        ExportTeacherSnapshot(name="Ada", acronym="AA")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# -- ExportSessionModifications
# ---------------------------------------------------------------------------


def test_modifications_default_all_declared_fields_to_none() -> None:
    modifications = ExportSessionModifications()
    dumped = modifications.model_dump()
    assert dumped["start_time"] is None
    assert dumped["rooms"] is None
    assert dumped["class_subjects"] is None


def test_modifications_allow_extra_columns() -> None:
    modifications = ExportSessionModifications.model_validate(
        {"custom_column": {"old": 1, "new": 2}},
    )
    assert modifications.model_dump()["custom_column"] == {"old": 1, "new": 2}


def test_modifications_parse_relation_buckets() -> None:
    modifications = ExportSessionModifications.model_validate(
        {"rooms": {"added": [{"room_id": "r1", "room_name": "B101"}], "removed": []}},
    )
    assert modifications.rooms is not None
    assert modifications.rooms.added[0].room_name == "B101"


# ---------------------------------------------------------------------------
# -- ExportModificationStep
# ---------------------------------------------------------------------------


def _minimal_step(step_type: str = "move") -> dict:
    return {
        "type": step_type,
        "original_block_id": "block-1",
        "session_ids": ["s1"],
        "weeks": ["2026-01-05"],
        "week_range": {"start": "2026-01-05", "end": "2026-01-05", "contiguous": True},
        "modifications": {},
        "dependencies": [],
        "session": {
            "id": "s1",
            "start_time": 830,
            "duration": 2,
            "weekday": "monday",
            "week": "2026-01-05",
        },
    }


@mark.parametrize("step_type", ["move", "exchange"])
def test_modification_step_accepts_valid_types(step_type: str) -> None:
    step = ExportModificationStep.model_validate(_minimal_step(step_type))
    assert step.type == step_type


@mark.parametrize("step_type", ["delete", "swap", "", "MOVE"])
def test_modification_step_rejects_invalid_types(step_type: str) -> None:
    with raises(ValidationError):
        ExportModificationStep.model_validate(_minimal_step(step_type))


def test_modification_step_applies_to_all_weeks_defaults_to_none() -> None:
    step = ExportModificationStep.model_validate(_minimal_step())
    assert step.applies_to_all_weeks is None


# ---------------------------------------------------------------------------
# -- Conflict models
# ---------------------------------------------------------------------------


def test_room_conflict_defaults_subject_labels_and_optional_weeks() -> None:
    conflict = ExportRoomConflict.model_validate(
        {
            "room_id": uuid.uuid7(),
            "room_name": "B101",
            "week": datetime.date(2026, 1, 5),
            "weekday": WeekDay.MONDAY,
            "start_time": 830,
            "duration": 2,
            "collisions": 2,
            "session_ids": [uuid.uuid7(), uuid.uuid7()],
        },
    )
    assert conflict.subject_labels == []
    assert conflict.weeks is None
    assert conflict.week == "2026-01-05"
    assert conflict.weekday == "monday"
    assert all(isinstance(sid, str) for sid in conflict.session_ids)


def test_teacher_conflict_requires_teacher_number_int() -> None:
    with raises(ValidationError):
        ExportTeacherConflict.model_validate(
            {
                "teacher_id": "t1",
                "teacher_number": "not-an-int",
                "teacher_acronym": "AA",
                "teacher_name": "Ada",
                "week": "2026-01-05",
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["s1"],
            },
        )


def test_class_conflict_coerces_identifiers() -> None:
    conflict = ExportClassConflict.model_validate(
        {
            "class_id": 1,
            "class_code": "1LEIC01",
            "week": "2026-01-05",
            "weekday": "monday",
            "start_time": 830,
            "duration": 2,
            "collisions": 3,
            "session_ids": ["s1", "s2", "s3"],
        },
    )
    assert conflict.class_id == "1"
    assert conflict.collisions == 3


# ---------------------------------------------------------------------------
# -- Payload envelopes
# ---------------------------------------------------------------------------


def test_project_export_payload_defaults_conflict_and_step_lists() -> None:
    payload = ProjectExportPayload.model_validate(
        {"added_removed_sessions": {"added": [], "removed": []}},
    )
    assert payload.rooms_conflicts == []
    assert payload.teacher_conflicts == []
    assert payload.classes_conflicts == []
    assert payload.modification_steps == []


def test_compact_payload_requires_exact_format_literal() -> None:
    valid = CompactProjectExportPayload.model_validate(
        {
            "format": "compact_export_v1",
            "entities": {},
            "added_removed_sessions": {"added": [], "removed": []},
        },
    )
    assert valid.format == "compact_export_v1"

    with raises(ValidationError):
        CompactProjectExportPayload.model_validate(
            {
                "format": "compact_export_v2",
                "entities": {},
                "added_removed_sessions": {"added": [], "removed": []},
            },
        )


def test_compact_payload_defaults_entity_maps() -> None:
    payload = CompactProjectExportPayload.model_validate(
        {
            "format": "compact_export_v1",
            "entities": {},
            "added_removed_sessions": {"added": [], "removed": []},
        },
    )
    assert payload.entities.rooms == {}
    assert payload.entities.sessions == {}
    assert payload.conflicts == []
    assert payload.modification_steps == []
