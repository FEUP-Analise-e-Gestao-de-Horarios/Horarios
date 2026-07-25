from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

type ExportPrimitive = str | int | float | bool | date | UUID | None
type ExportJsonValue = ExportPrimitive | list[ExportJsonValue] | dict[str, ExportJsonValue]
type PayloadFormat = Literal["compact", "expanded"]
type CompactExportConflictKind = Literal["room", "teacher", "class"]


def stringify_export_value(value: ExportPrimitive) -> str:
    """Coerce scalar exporter values to strings for JSON-facing id/date fields."""
    return str(value)


def stringify_optional_export_value(value: ExportPrimitive) -> str | None:
    """Coerce optional scalar exporter values to strings while preserving nulls."""
    return None if value is None else str(value)


type ExportString = Annotated[str, BeforeValidator(stringify_export_value)]
type ExportOptionalString = Annotated[str | None, BeforeValidator(stringify_optional_export_value)]


class ExportAddedRemovedRecords[T](BaseModel):
    """Generic added/removed bucket used for sessions and relation diffs."""

    added: list[T] = Field(default_factory=list)
    removed: list[T] = Field(default_factory=list)


class ExportRoomRelationChange(BaseModel):
    """Expanded room relation row embedded in modification diffs."""

    room_id: ExportString
    room_name: ExportOptionalString = None
    room_type: ExportOptionalString = None
    room_size: ExportOptionalString = None
    room_seats: ExportOptionalString = None


class ExportTeacherRelationChange(BaseModel):
    """Expanded teacher relation row embedded in modification diffs."""

    teacher_id: ExportString
    teacher_number: int | None = None
    teacher_acronym: ExportOptionalString = None
    teacher_name: ExportOptionalString = None


class ExportClassSubjectRelationChange(BaseModel):
    """Expanded class-subject relation row embedded in modification diffs."""

    class_id: ExportString
    class_code: ExportOptionalString = None
    class_shift: int | None = None
    subject_id: ExportString
    subject_number: int | None = None
    subject_code: ExportOptionalString = None
    subject_acronym: ExportOptionalString = None
    subject_name: ExportOptionalString = None


class ExportColumnChange(BaseModel):
    """Old/new value pair for a modified scalar session column."""

    old: ExportJsonValue
    new: ExportJsonValue


class ExportSessionModifications(BaseModel):
    """Field-level modifications for one exported session or recurring group."""

    model_config = ConfigDict(extra="allow")

    __pydantic_extra__: dict[str, ExportJsonValue] = Field(init=False)

    start_time: ExportColumnChange | None = None
    duration: ExportColumnChange | None = None
    weekday: ExportColumnChange | None = None
    week: ExportColumnChange | None = None
    type: ExportColumnChange | None = None
    original_block_id: ExportColumnChange | None = None
    rooms: ExportAddedRemovedRecords[ExportRoomRelationChange] | None = None
    teachers: ExportAddedRemovedRecords[ExportTeacherRelationChange] | None = None
    class_subjects: ExportAddedRemovedRecords[ExportClassSubjectRelationChange] | None = None


class ExportTeacherSnapshot(BaseModel):
    """Teacher details shown in the expanded session snapshot."""

    number: int
    name: ExportString
    acronym: ExportString


class ExportSubjectSnapshot(BaseModel):
    """Subject details shown in the expanded session snapshot."""

    name: ExportString
    acronym: ExportOptionalString = None
    code: ExportString


class ExportSessionRecord(BaseModel):
    """Session row shown in the added/removed exporter section."""

    id: ExportString
    original_block_id: ExportOptionalString = None
    start_time: int | None = None
    duration: int | None = None
    weekday: ExportOptionalString = None
    week: ExportOptionalString = None
    type: ExportOptionalString = None
    room_ids: list[ExportString] = Field(default_factory=list)
    rooms: list[ExportString] = Field(default_factory=list)
    room_details: list[ExportRoomRelationChange] = Field(default_factory=list)
    teacher_ids: list[ExportString] = Field(default_factory=list)
    teachers: list[ExportTeacherSnapshot] = Field(default_factory=list)
    teacher_details: list[ExportTeacherRelationChange] = Field(default_factory=list)
    class_ids: list[ExportString] = Field(default_factory=list)
    classes: list[ExportString] = Field(default_factory=list)
    subject_ids: list[ExportString] = Field(default_factory=list)
    subjects: list[ExportSubjectSnapshot] = Field(default_factory=list)


class ExportSessionSnapshot(BaseModel):
    """Public session snapshot attached to an expanded modification step."""

    model_config = ConfigDict(extra="allow")

    __pydantic_extra__: dict[str, ExportJsonValue] = Field(init=False)

    id: ExportString
    original_block_id: ExportOptionalString = None
    start_time: int
    duration: int
    weekday: ExportString
    week: ExportString
    rooms: list[ExportString] = Field(default_factory=list)
    room_details: list[ExportRoomRelationChange] = Field(default_factory=list)
    teachers: list[ExportTeacherSnapshot] = Field(default_factory=list)
    classes: list[ExportString] = Field(default_factory=list)
    subjects: list[ExportSubjectSnapshot] = Field(default_factory=list)


class ExportWeekRange(BaseModel):
    """Display-friendly range metadata for recurring-week grouped steps."""

    start: ExportOptionalString
    end: ExportOptionalString
    contiguous: bool


class ExportModificationStep(BaseModel):
    """Expanded exporter instruction describing a move or exchange step."""

    type: Literal["move", "exchange"]
    original_block_id: ExportString
    session_ids: list[ExportString]
    weeks: list[ExportString]
    week_range: ExportWeekRange
    applies_to_all_weeks: bool | None = None
    modifications: ExportSessionModifications
    dependencies: list[ExportString]
    session: ExportSessionSnapshot
    dependency_conflicts: dict[str, list[str]] = Field(default_factory=dict)


class ExportConflictBase(BaseModel):
    """Common timing and collision details for resource conflict rows."""

    week: ExportString
    weeks: list[ExportString] | None = None
    weekday: ExportString
    start_time: int
    duration: int
    collisions: int
    session_ids: list[ExportString]
    subject_labels: list[ExportString] = Field(default_factory=list)


class ExportRoomConflict(ExportConflictBase):
    """Expanded conflict row for a room resource."""

    room_id: ExportString
    room_name: ExportString


class ExportTeacherConflict(ExportConflictBase):
    """Expanded conflict row for a teacher resource."""

    teacher_id: ExportString
    teacher_number: int
    teacher_acronym: ExportString
    teacher_name: ExportString


class ExportClassConflict(ExportConflictBase):
    """Expanded conflict row for a class resource."""

    class_id: ExportString
    class_code: ExportString


class ProjectExportPayload(BaseModel):
    """Legacy expanded exporter payload consumed by existing frontend views."""

    added_removed_sessions: ExportAddedRemovedRecords[ExportSessionRecord]
    rooms_conflicts: list[ExportRoomConflict] = Field(default_factory=list)
    teacher_conflicts: list[ExportTeacherConflict] = Field(default_factory=list)
    classes_conflicts: list[ExportClassConflict] = Field(default_factory=list)
    modification_steps: list[ExportModificationStep] = Field(default_factory=list)
    checked_item_keys: list[ExportString] = Field(default_factory=list)


class CompactExportEntities(BaseModel):
    """Normalized entity maps referenced by compact conflicts and steps."""

    rooms: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    teachers: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    classes: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    subjects: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    sessions: dict[str, ExportSessionSnapshot] = Field(default_factory=dict)


type LegacyCompactExportConflict = tuple[
    CompactExportConflictKind,
    ExportString,
    ExportString,
    list[ExportString] | None,
    ExportString,
    int,
    int,
    int,
    list[str],
]

type CompactExportConflict = (
    tuple[
        CompactExportConflictKind,
        ExportString,
        ExportString,
        list[ExportString] | None,
        ExportString,
        int,
        int,
        int,
        list[str],
        list[ExportString],
    ]
    | LegacyCompactExportConflict
)


class CompactExportModificationStep(BaseModel):
    """Compact modification step with session data moved into entity maps."""

    model_config = ConfigDict(extra="allow")

    __pydantic_extra__: dict[str, ExportJsonValue] = Field(init=False)

    type: Literal["move", "exchange"]
    original_block_id: ExportString
    session_ids: list[ExportString]
    weeks: list[ExportString]
    week_range: ExportWeekRange
    applies_to_all_weeks: bool | None = None
    modifications: dict[str, ExportJsonValue] = Field(default_factory=dict)
    dependencies: list[ExportString]


class CompactProjectExportPayload(BaseModel):
    """Canonical compact exporter payload stored in cache and sent on request."""

    format: Literal["compact_export_v1"]
    entities: CompactExportEntities
    added_removed_sessions: ExportAddedRemovedRecords[ExportSessionRecord]
    conflicts: list[CompactExportConflict] = Field(default_factory=list)
    modification_steps: list[CompactExportModificationStep] = Field(default_factory=list)
    checked_item_keys: list[ExportString] = Field(default_factory=list)


type ExportPayload = ProjectExportPayload | CompactProjectExportPayload
