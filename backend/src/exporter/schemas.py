from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

type ExportPrimitive = str | int | float | bool | None | date | UUID
type ExportJsonValue = ExportPrimitive | list[ExportJsonValue] | dict[str, ExportJsonValue]
type PayloadFormat = Literal["compact", "expanded"]
type CompactExportConflictKind = Literal["room", "teacher", "class"]


def stringify_export_value(value: ExportPrimitive) -> str:
    return str(value)


def stringify_optional_export_value(value: ExportPrimitive) -> str | None:
    return None if value is None else str(value)


type ExportString = Annotated[str, BeforeValidator(stringify_export_value)]
type ExportOptionalString = Annotated[str | None, BeforeValidator(stringify_optional_export_value)]


class ExportAddedRemovedRecords[T](BaseModel):
    added: list[T] = Field(default_factory=list)
    removed: list[T] = Field(default_factory=list)


class ExportSessionRecord(BaseModel):
    id: ExportString


class ExportRoomRelationChange(BaseModel):
    room_id: ExportString
    room_name: ExportOptionalString = None
    room_type: ExportOptionalString = None
    room_size: ExportOptionalString = None
    room_seats: ExportOptionalString = None


class ExportTeacherRelationChange(BaseModel):
    teacher_id: ExportString
    teacher_number: int | None = None
    teacher_acronym: ExportOptionalString = None
    teacher_name: ExportOptionalString = None


class ExportClassSubjectRelationChange(BaseModel):
    class_id: ExportString
    class_code: ExportOptionalString = None
    class_shift: int | None = None
    subject_id: ExportString
    subject_number: int | None = None
    subject_code: ExportOptionalString = None
    subject_acronym: ExportOptionalString = None
    subject_name: ExportOptionalString = None


class ExportColumnChange(BaseModel):
    old: ExportJsonValue
    new: ExportJsonValue


class ExportSessionModifications(BaseModel):
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
    number: int
    name: ExportString
    acronym: ExportString


class ExportSubjectSnapshot(BaseModel):
    name: ExportString
    acronym: ExportOptionalString = None
    code: ExportString


class ExportSessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    __pydantic_extra__: dict[str, ExportJsonValue] = Field(init=False)

    id: ExportString
    original_block_id: ExportOptionalString = None
    start_time: int
    duration: int
    weekday: ExportString
    week: ExportString
    rooms: list[ExportString] = Field(default_factory=list)
    teachers: list[ExportTeacherSnapshot] = Field(default_factory=list)
    classes: list[ExportString] = Field(default_factory=list)
    subjects: list[ExportSubjectSnapshot] = Field(default_factory=list)


class ExportWeekRange(BaseModel):
    start: ExportOptionalString
    end: ExportOptionalString
    contiguous: bool


class ExportModificationStep(BaseModel):
    type: Literal["move", "exchange"]
    original_block_id: ExportString
    session_ids: list[ExportString]
    weeks: list[ExportString]
    week_range: ExportWeekRange
    applies_to_all_weeks: bool | None = None
    modifications: ExportSessionModifications
    dependencies: list[ExportString]
    session: ExportSessionSnapshot


class ExportConflictBase(BaseModel):
    week: ExportString
    weeks: list[ExportString] | None = None
    weekday: ExportString
    start_time: int
    duration: int
    collisions: int
    session_ids: list[ExportString]


class ExportRoomConflict(ExportConflictBase):
    room_id: ExportString
    room_name: ExportString


class ExportTeacherConflict(ExportConflictBase):
    teacher_id: ExportString
    teacher_number: int
    teacher_acronym: ExportString
    teacher_name: ExportString


class ExportClassConflict(ExportConflictBase):
    class_id: ExportString
    class_code: ExportString


class ProjectExportPayload(BaseModel):
    added_removed_sessions: ExportAddedRemovedRecords[ExportSessionRecord]
    rooms_conflicts: list[ExportRoomConflict] = Field(default_factory=list)
    teacher_conflicts: list[ExportTeacherConflict] = Field(default_factory=list)
    classes_conflicts: list[ExportClassConflict] = Field(default_factory=list)
    modification_steps: list[ExportModificationStep] = Field(default_factory=list)


class CompactExportEntities(BaseModel):
    rooms: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    teachers: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    classes: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    subjects: dict[str, dict[str, ExportJsonValue]] = Field(default_factory=dict)
    sessions: dict[str, ExportSessionSnapshot] = Field(default_factory=dict)


type CompactExportConflict = tuple[
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


class CompactExportModificationStep(BaseModel):
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
    format: Literal["compact_export_v1"]
    entities: CompactExportEntities
    added_removed_sessions: ExportAddedRemovedRecords[ExportSessionRecord]
    conflicts: list[CompactExportConflict] = Field(default_factory=list)
    modification_steps: list[CompactExportModificationStep] = Field(default_factory=list)


type ExportPayload = ProjectExportPayload | CompactProjectExportPayload
