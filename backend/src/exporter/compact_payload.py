from copy import deepcopy
from typing import Any

COMPACT_EXPORT_FORMAT = "compact_export_v1"


def compact_export_payload(expanded: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, normalized exporter payload for transport/cache storage."""
    entities: dict[str, dict[str, Any]] = {
        "rooms": {},
        "teachers": {},
        "classes": {},
        "subjects": {},
        "sessions": {},
    }

    compact_conflicts = [
        compact_conflict(kind, conflict, entities)
        for kind, rows in (
            ("room", expanded.get("rooms_conflicts", [])),
            ("teacher", expanded.get("teacher_conflicts", [])),
            ("class", expanded.get("classes_conflicts", [])),
        )
        for conflict in rows
    ]

    compact_steps = [
        compact_modification_step(step, entities) for step in expanded.get("modification_steps", [])
    ]

    return {
        "format": COMPACT_EXPORT_FORMAT,
        "entities": entities,
        "added_removed_sessions": deepcopy(expanded.get("added_removed_sessions", {})),
        "conflicts": compact_conflicts,
        "modification_steps": compact_steps,
    }


def expand_compact_export_payload(compact: dict[str, Any]) -> dict[str, Any]:
    """Expand a compact exporter payload into the legacy frontend view model."""
    if compact.get("format") != COMPACT_EXPORT_FORMAT:
        return compact

    entities = compact.get("entities", {})
    conflicts = compact.get("conflicts", [])
    return {
        "added_removed_sessions": deepcopy(compact.get("added_removed_sessions", {})),
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
            for step in compact.get("modification_steps", [])
        ],
    }


def compact_conflict_kind(conflict: Any) -> str | None:
    if isinstance(conflict, list) and conflict:
        return str(conflict[0])
    if isinstance(conflict, dict):
        return conflict.get("kind")
    return None


def compact_conflict(
    kind: str,
    conflict: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
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
        entities["rooms"].setdefault(
            resource_id,
            {
                "room_name": conflict["room_name"],
            },
        )
    elif kind == "teacher":
        resource_id = str(conflict["teacher_id"])
        entities["teachers"].setdefault(
            resource_id,
            {
                "teacher_number": conflict["teacher_number"],
                "teacher_acronym": conflict["teacher_acronym"],
                "teacher_name": conflict["teacher_name"],
            },
        )
    elif kind == "class":
        resource_id = str(conflict["class_id"])
        entities["classes"].setdefault(
            resource_id,
            {
                "class_code": conflict["class_code"],
            },
        )
    else:
        raise ValueError(f"Unknown compact conflict kind: {kind}")

    return [
        kind,
        resource_id,
        compact["week"],
        compact.get("weeks"),
        compact["weekday"],
        compact["start_time"],
        compact["duration"],
        compact["collisions"],
        compact["session_ids"],
    ]


def expand_conflict(
    conflict: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if isinstance(conflict, list):
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
        expanded = {
            "week": week,
            "weeks": weeks,
            "weekday": weekday,
            "start_time": start_time,
            "duration": duration,
            "collisions": collisions,
            "session_ids": session_ids,
        }
    else:
        kind = conflict["kind"]
        resource_id = str(conflict["resource_id"])
        expanded = {
            key: deepcopy(value)
            for key, value in conflict.items()
            if key not in {"kind", "resource_id"}
        }

    resource_id = str(resource_id)

    if kind == "room":
        expanded.update({"room_id": resource_id, **entities.get("rooms", {}).get(resource_id, {})})
    elif kind == "teacher":
        expanded.update(
            {"teacher_id": resource_id, **entities.get("teachers", {}).get(resource_id, {})},
        )
    elif kind == "class":
        expanded.update(
            {"class_id": resource_id, **entities.get("classes", {}).get(resource_id, {})},
        )
    else:
        raise ValueError(f"Unknown compact conflict kind: {kind}")

    return expanded


def compact_modification_step(
    step: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    session = deepcopy(step["session"])
    session_id = str(session["id"])
    entities["sessions"].setdefault(session_id, session)

    compact = {
        key: deepcopy(value)
        for key, value in step.items()
        if key not in {"session", "modifications"}
    }
    compact["modifications"] = compact_modifications(step.get("modifications", {}), entities)
    return compact


def expand_modification_step(
    step: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    session_id = str(step["session_ids"][0])
    expanded = {key: deepcopy(value) for key, value in step.items()}
    expanded["session"] = deepcopy(entities.get("sessions", {}).get(session_id, {"id": session_id}))
    expanded["modifications"] = expand_modifications(
        step.get("modifications", {}),
        entities,
    )
    return expanded


def compact_modifications(
    modifications: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for field, change in modifications.items():
        if field == "rooms":
            compact[field] = compact_relation_change(change, "room_id", "rooms", entities)
        elif field == "teachers":
            compact[field] = compact_relation_change(change, "teacher_id", "teachers", entities)
        elif field == "class_subjects":
            compact[field] = compact_class_subject_change(change, entities)
        else:
            compact[field] = deepcopy(change)
    return compact


def expand_modifications(
    modifications: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expanded: dict[str, Any] = {}
    for field, change in modifications.items():
        if field == "rooms":
            expanded[field] = expand_relation_change(change, "room_id", "rooms", entities)
        elif field == "teachers":
            expanded[field] = expand_relation_change(change, "teacher_id", "teachers", entities)
        elif field == "class_subjects":
            expanded[field] = expand_class_subject_change(change, entities)
        else:
            expanded[field] = deepcopy(change)
    return expanded


def compact_relation_change(
    change: dict[str, Any],
    id_key: str,
    entity_key: str,
    entities: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    compact = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        for record in change.get(change_type, []):
            entity_id = str(record[id_key])
            entities[entity_key].setdefault(
                entity_id,
                {key: deepcopy(value) for key, value in record.items() if key != id_key},
            )
            compact[change_type].append(entity_id)
    return compact


def expand_relation_change(
    change: dict[str, Any],
    id_key: str,
    entity_key: str,
    entities: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    expanded = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        for record in change.get(change_type, []):
            entity_id = str(record[id_key] if isinstance(record, dict) else record)
            expanded[change_type].append(
                {id_key: entity_id, **deepcopy(entities.get(entity_key, {}).get(entity_id, {}))},
            )
    return expanded


def compact_class_subject_change(
    change: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, list[list[str]]]:
    compact = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        for record in change.get(change_type, []):
            class_id = str(record["class_id"])
            subject_id = str(record["subject_id"])
            entities["classes"].setdefault(
                class_id,
                {key: deepcopy(value) for key, value in record.items() if key.startswith("class_")},
            )
            entities["subjects"].setdefault(
                subject_id,
                {
                    key: deepcopy(value)
                    for key, value in record.items()
                    if key.startswith("subject_")
                },
            )
            compact[change_type].append([class_id, subject_id])
    return compact


def expand_class_subject_change(
    change: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    expanded = {"added": [], "removed": []}
    for change_type in ("added", "removed"):
        for record in change.get(change_type, []):
            if isinstance(record, list):
                class_id, subject_id = map(str, record)
            else:
                class_id = str(record["class_id"])
                subject_id = str(record["subject_id"])
            expanded[change_type].append(
                {
                    "class_id": class_id,
                    **deepcopy(entities.get("classes", {}).get(class_id, {"class_id": class_id})),
                    "subject_id": subject_id,
                    **deepcopy(
                        entities.get("subjects", {}).get(subject_id, {"subject_id": subject_id}),
                    ),
                },
            )
    return expanded
