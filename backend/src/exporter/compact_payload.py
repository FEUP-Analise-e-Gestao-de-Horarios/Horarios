from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import cast

from src.exporter.schemas import (
    CompactExportConflict,
    CompactExportConflictKind,
    CompactProjectExportPayload,
    ExportJsonValue,
    ProjectExportPayload,
)

COMPACT_EXPORT_FORMAT = "compact_export_v1"

type ExportMapping = dict[str, ExportJsonValue]
type ExportRecord = Mapping[str, ExportJsonValue]
type EntityMaps = dict[str, ExportMapping]
type CompactConflictRecord = CompactExportConflict | ExportRecord
type RelationRecord = ExportRecord
type CompactRelationRecord = RelationRecord | str
type CompactClassSubjectRecord = RelationRecord | Sequence[str]


def normalize_compact_id(value: ExportJsonValue) -> str:
    """Return an id string in the comparison form used across compact lookups."""
    return str(value).replace("-", "")


def merge_entity_fields(
    entity_map: ExportMapping,
    entity_id: str,
    fields: ExportRecord,
) -> None:
    """Accumulate ``fields`` into one entity, keeping the first value seen per key.

    Entities are populated from several sources — resource conflicts and the
    added/removed relation rows of modification steps — that each know only a
    subset of an entity's fields (a conflict knows a class code but not its
    shift, for example). Merging per key, rather than replacing the whole entity
    via ``setdefault``, means no source's fields are dropped no matter which one
    is compacted first.

    ``None`` values are ignored: they mark a field a particular source did not
    provide, so they must never win a ``setdefault`` slot over a real value nor
    bloat the compact payload (the expander re-materializes absent fields as
    ``None`` anyway).
    """
    entity = cast(ExportMapping, entity_map.setdefault(entity_id, {}))
    for key, value in fields.items():
        if value is None:
            continue
        entity.setdefault(key, deepcopy(value))


def find_entity(entities: EntityMaps, entity_key: str, entity_id: ExportJsonValue) -> ExportMapping:
    """Return an entity by exact id or UUID-normalized id."""
    entity_map = entities.get(entity_key, {})
    exact_id = str(entity_id)
    exact = entity_map.get(exact_id)
    if isinstance(exact, Mapping):
        return dict(exact)

    normalized_id = normalize_compact_id(entity_id)
    normalized = entity_map.get(normalized_id)
    if isinstance(normalized, Mapping):
        return dict(normalized)

    for key, value in entity_map.items():
        if normalize_compact_id(key) == normalized_id and isinstance(value, Mapping):
            return dict(value)

    return {}


def compact_export_payload(
    expanded: ProjectExportPayload | ExportRecord,
) -> CompactProjectExportPayload:
    """Return a compact, normalized exporter payload for transport/cache storage."""
    expanded_data = ProjectExportPayload.model_validate(expanded).model_dump(mode="json")
    entities: EntityMaps = {
        "rooms": {},
        "teachers": {},
        "classes": {},
        "subjects": {},
        "sessions": {},
    }

    compact_conflicts = [
        compact_conflict(kind, conflict, entities)
        for kind, rows in (
            ("room", expanded_data.get("rooms_conflicts", [])),
            ("teacher", expanded_data.get("teacher_conflicts", [])),
            ("class", expanded_data.get("classes_conflicts", [])),
        )
        for conflict in cast(Sequence[ExportRecord], rows)
    ]

    compact_steps = [
        compact_modification_step(step, entities)
        for step in cast(Sequence[ExportRecord], expanded_data.get("modification_steps", []))
    ]

    return CompactProjectExportPayload.model_validate(
        {
            "format": COMPACT_EXPORT_FORMAT,
            "entities": entities,
            "added_removed_sessions": deepcopy(expanded_data.get("added_removed_sessions", {})),
            "conflicts": compact_conflicts,
            "modification_steps": compact_steps,
            "checked_item_keys": deepcopy(expanded_data.get("checked_item_keys", [])),
        },
    )


def expand_compact_export_payload(
    compact: CompactProjectExportPayload | ExportRecord,
) -> ProjectExportPayload:
    """Expand a compact exporter payload into the legacy frontend view model."""
    compact_data = CompactProjectExportPayload.model_validate(compact).model_dump(mode="json")
    entities = cast(EntityMaps, compact_data.get("entities", {}))
    conflicts = cast(Sequence[CompactConflictRecord], compact_data.get("conflicts", []))

    return ProjectExportPayload.model_validate(
        {
            "added_removed_sessions": deepcopy(compact_data.get("added_removed_sessions", {})),
            "rooms_conflicts": [
                expand_conflict(conflict, entities)
                for conflict in conflicts
                if compact_conflict_kind(conflict) == "room"
            ],
            "teacher_conflicts": [
                expand_conflict(conflict, entities)
                for conflict in conflicts
                if compact_conflict_kind(conflict) == "teacher"
            ],
            "classes_conflicts": [
                expand_conflict(conflict, entities)
                for conflict in conflicts
                if compact_conflict_kind(conflict) == "class"
            ],
            "modification_steps": [
                expand_modification_step(step, entities)
                for step in cast(
                    Sequence[ExportRecord],
                    compact_data.get("modification_steps", []),
                )
            ],
            "checked_item_keys": deepcopy(compact_data.get("checked_item_keys", [])),
        },
    )


def compact_conflict_kind(conflict: CompactConflictRecord) -> str | None:
    """Return the resource kind from either tuple-style or dict-style compact conflicts."""
    if isinstance(conflict, list | tuple) and conflict:
        return str(conflict[0])
    if isinstance(conflict, Mapping):
        kind = conflict.get("kind")
        return str(kind) if kind is not None else None
    return None


def compact_conflict(
    kind: CompactExportConflictKind,
    conflict: ExportRecord,
    entities: EntityMaps,
) -> CompactExportConflict:
    """Normalize one expanded conflict row and store repeated resource data in entities."""
    compact = {
        key: deepcopy(value)
        for key, value in conflict.items()
        if key
        not in {
            "room_id",
            "room_name",
            "teacher_id",
            "teacher_number",
            "teacher_acronym",
            "teacher_name",
            "class_id",
            "class_code",
        }
    }

    if kind == "room":
        resource_id = str(conflict["room_id"])
        merge_entity_fields(
            entities["rooms"],
            resource_id,
            {"room_name": conflict["room_name"]},
        )
    elif kind == "teacher":
        resource_id = str(conflict["teacher_id"])
        merge_entity_fields(
            entities["teachers"],
            resource_id,
            {
                "teacher_number": conflict["teacher_number"],
                "teacher_acronym": conflict["teacher_acronym"],
                "teacher_name": conflict["teacher_name"],
            },
        )
    elif kind == "class":
        resource_id = str(conflict["class_id"])
        merge_entity_fields(
            entities["classes"],
            resource_id,
            {"class_code": conflict["class_code"]},
        )
    else:
        raise ValueError(f"Unknown compact conflict kind: {kind}")

    return (
        kind,
        resource_id,
        str(compact["week"]),
        cast(list[str] | None, compact.get("weeks")),
        str(compact["weekday"]),
        cast(int, compact["start_time"]),
        cast(int, compact["duration"]),
        cast(int, compact["collisions"]),
        cast(list[str], compact["session_ids"]),
        cast(list[str], compact.get("subject_labels", [])),
    )


def expand_conflict(conflict: CompactConflictRecord, entities: EntityMaps) -> ExportMapping:
    """Rebuild one legacy expanded conflict row from a compact conflict record."""
    if isinstance(conflict, list | tuple):
        if len(conflict) == 9:
            (
                kind,
                resource_id,
                week,
                weeks,
                weekday,
                start_time,
                duration,
                collisions,
                session_ids,
            ) = conflict
            subject_labels = []
        else:
            (
                kind,
                resource_id,
                week,
                weeks,
                weekday,
                start_time,
                duration,
                collisions,
                session_ids,
                subject_labels,
            ) = conflict
        expanded: ExportMapping = {
            "week": week,
            "weeks": weeks,
            "weekday": weekday,
            "start_time": start_time,
            "duration": duration,
            "collisions": collisions,
            "session_ids": session_ids,
            "subject_labels": subject_labels,
        }
    else:
        conflict_mapping = cast(ExportRecord, conflict)
        kind = conflict_mapping["kind"]
        resource_id = str(conflict_mapping["resource_id"])
        expanded = {
            key: deepcopy(value)
            for key, value in conflict_mapping.items()
            if key not in {"kind", "resource_id"}
        }

    resource_id = str(resource_id)

    if kind == "room":
        expanded.update({"room_id": resource_id, **find_entity(entities, "rooms", resource_id)})
    elif kind == "teacher":
        expanded.update(
            {"teacher_id": resource_id, **find_entity(entities, "teachers", resource_id)},
        )
    elif kind == "class":
        expanded.update(
            {"class_id": resource_id, **find_entity(entities, "classes", resource_id)},
        )
    else:
        raise ValueError(f"Unknown compact conflict kind: {kind}")

    return expanded


def compact_modification_step(step: ExportRecord, entities: EntityMaps) -> ExportMapping:
    """Replace an expanded modification step's session/details with normalized references."""
    session = cast(ExportMapping, deepcopy(step["session"]))
    session_id = str(session["id"])
    entities["sessions"].setdefault(session_id, session)

    compact = {
        key: deepcopy(value)
        for key, value in step.items()
        if key not in {"session", "modifications"}
    }
    compact["modifications"] = compact_modifications(
        cast(ExportRecord, step.get("modifications", {})),
        entities,
    )
    return compact


def expand_modification_step(step: ExportRecord, entities: EntityMaps) -> ExportMapping:
    """Rebuild one legacy modification step from compact normalized entities."""
    session_ids = cast(Sequence[ExportJsonValue], step["session_ids"])
    session_id = str(session_ids[0])
    expanded = dict(deepcopy(step))
    expanded["session"] = deepcopy(
        find_entity(entities, "sessions", session_id) or {"id": session_id},
    )
    expanded["modifications"] = expand_modifications(
        cast(ExportRecord, step.get("modifications", {})),
        entities,
    )
    return expanded


def compact_modifications(
    modifications: ExportRecord,
    entities: EntityMaps,
) -> ExportMapping:
    """Compact relation modifications while preserving scalar column changes."""
    compact: ExportMapping = {}
    for field, change in modifications.items():
        if change is None:
            continue
        change_mapping = cast(ExportRecord, change)
        if field == "rooms":
            compact[field] = compact_relation_change(change_mapping, "room_id", "rooms", entities)
        elif field == "teachers":
            compact[field] = compact_relation_change(
                change_mapping,
                "teacher_id",
                "teachers",
                entities,
            )
        elif field == "class_subjects":
            compact[field] = compact_class_subject_change(change_mapping, entities)
        else:
            compact[field] = deepcopy(change)
    return compact


def expand_modifications(
    modifications: ExportRecord,
    entities: EntityMaps,
) -> ExportMapping:
    """Expand compact relation modifications back to the legacy relation payloads."""
    expanded: ExportMapping = {}
    for field, change in modifications.items():
        if change is None:
            continue
        change_mapping = cast(ExportRecord, change)
        if field == "rooms":
            expanded[field] = expand_relation_change(change_mapping, "room_id", "rooms", entities)
        elif field == "teachers":
            expanded[field] = expand_relation_change(
                change_mapping,
                "teacher_id",
                "teachers",
                entities,
            )
        elif field == "class_subjects":
            expanded[field] = expand_class_subject_change(change_mapping, entities)
        else:
            expanded[field] = deepcopy(change)
    return expanded


def compact_relation_change(
    change: ExportRecord,
    id_key: str,
    entity_key: str,
    entities: EntityMaps,
) -> dict[str, list[str]]:
    """Normalize added/removed room or teacher relation rows into entity id lists."""
    compact: dict[str, list[str]] = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        records = cast(Sequence[RelationRecord], change.get(change_type, []))
        for record in records:
            entity_id = str(record[id_key])
            merge_entity_fields(
                entities[entity_key],
                entity_id,
                {key: value for key, value in record.items() if key != id_key},
            )
            compact[change_type].append(entity_id)
    return compact


def expand_relation_change(
    change: ExportRecord,
    id_key: str,
    entity_key: str,
    entities: EntityMaps,
) -> dict[str, list[ExportMapping]]:
    """Expand compact room or teacher id lists into full added/removed relation rows."""
    expanded: dict[str, list[ExportMapping]] = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        records = cast(Sequence[CompactRelationRecord], change.get(change_type, []))
        for record in records:
            entity_id = str(
                cast(RelationRecord, record)[id_key] if isinstance(record, Mapping) else record,
            )
            expanded[change_type].append(
                {id_key: entity_id, **deepcopy(find_entity(entities, entity_key, entity_id))},
            )
    return expanded


def compact_class_subject_change(
    change: ExportRecord,
    entities: EntityMaps,
) -> dict[str, list[list[str]]]:
    """Normalize class-subject relation changes into class/subject id pairs."""
    compact: dict[str, list[list[str]]] = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        records = cast(Sequence[RelationRecord], change.get(change_type, []))
        for record in records:
            class_id = str(record["class_id"])
            subject_id = str(record["subject_id"])
            merge_entity_fields(
                entities["classes"],
                class_id,
                {
                    key: value
                    for key, value in record.items()
                    if key.startswith("class_") and key != "class_id"
                },
            )
            merge_entity_fields(
                entities["subjects"],
                subject_id,
                {
                    key: value
                    for key, value in record.items()
                    if key.startswith("subject_") and key != "subject_id"
                },
            )
            compact[change_type].append([class_id, subject_id])
    return compact


def expand_class_subject_change(
    change: ExportRecord,
    entities: EntityMaps,
) -> dict[str, list[ExportMapping]]:
    """Expand compact class/subject id pairs into full class-subject relation rows."""
    expanded: dict[str, list[ExportMapping]] = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        records = cast(Sequence[CompactClassSubjectRecord], change.get(change_type, []))
        for record in records:
            if isinstance(record, list | tuple):
                class_id, subject_id = map(str, record)
            else:
                record_mapping = cast(RelationRecord, record)
                class_id = str(record_mapping["class_id"])
                subject_id = str(record_mapping["subject_id"])
            expanded[change_type].append(
                {
                    "class_id": class_id,
                    **deepcopy(
                        {
                            key: value
                            for key, value in find_entity(entities, "classes", class_id).items()
                            if key in {"class_code", "class_shift"}
                        },
                    ),
                    "subject_id": subject_id,
                    **deepcopy(
                        find_entity(entities, "subjects", subject_id) or {"subject_id": subject_id},
                    ),
                },
            )
    return expanded
