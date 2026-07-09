import type {
  CompactProjectExportPayload,
  ExportAddedRemovedRecords,
  ExportClassConflict,
  ExportClassSubjectRelationChange,
  ExportFieldModification,
  ExportModificationStep,
  ExportRoomConflict,
  ExportRoomRelationChange,
  ExportSessionRecord,
  ExportSessionModifications,
  ExportTeacherConflict,
  ExportTeacherRelationChange,
  ProjectExportApiPayload,
  ProjectExportPayload,
} from "@/types/exporter";

export function isCompactExportPayload(
  payload: ProjectExportApiPayload,
): payload is CompactProjectExportPayload {
  return "format" in payload && payload.format === "compact_export_v1";
}

export function compactExportToProjectExportPayload(
  payload: ProjectExportApiPayload,
): ProjectExportPayload {
  if (!isCompactExportPayload(payload)) {
    return payload;
  }

  return {
    added_removed_sessions: expandAddedRemovedSessions(payload.added_removed_sessions, payload),
    rooms_conflicts: payload.conflicts
      .filter((conflict) => conflict[0] === "room")
      .map((conflict): ExportRoomConflict => {
        const room = findEntity(payload.entities.rooms, conflict[1]);
        return {
          ...baseConflict(conflict),
          room_id: conflict[1],
          room_name: room?.room_name ?? conflict[1],
        };
      }),
    teacher_conflicts: payload.conflicts
      .filter((conflict) => conflict[0] === "teacher")
      .map((conflict): ExportTeacherConflict => {
        const teacher = findEntity(payload.entities.teachers, conflict[1]);
        return {
          ...baseConflict(conflict),
          teacher_id: conflict[1],
          teacher_number: teacher?.teacher_number ?? 0,
          teacher_acronym: teacher?.teacher_acronym ?? conflict[1],
          teacher_name: teacher?.teacher_name ?? conflict[1],
        };
      }),
    classes_conflicts: payload.conflicts
      .filter((conflict) => conflict[0] === "class")
      .map((conflict): ExportClassConflict => {
        const classEntity = findEntity(payload.entities.classes, conflict[1]);
        return {
          ...baseConflict(conflict),
          class_id: conflict[1],
          class_code: classEntity?.class_code ?? conflict[1],
        };
      }),
    modification_steps: payload.modification_steps.map((step): ExportModificationStep => ({
      ...step,
      session: sessionForStep(step, payload),
      modifications: expandModifications(step.modifications, payload),
    })),
    checked_item_keys: payload.checked_item_keys ?? [],
  };
}

function expandAddedRemovedSessions(
  records: CompactProjectExportPayload["added_removed_sessions"],
  payload: CompactProjectExportPayload,
): ExportAddedRemovedRecords<ExportSessionRecord> {
  const added = Array.isArray(records.added) ? records.added : [];
  const removed = Array.isArray(records.removed) ? records.removed : [];

  return {
    added: added.map((record) => expandSessionRecord(record, payload)),
    removed: removed.map((record) => expandSessionRecord(record, payload)),
  };
}

function expandSessionRecord(
  record: ExportSessionRecord,
  payload: CompactProjectExportPayload,
): ExportSessionRecord {
  const roomDetails = (record.room_ids ?? [])
    .map((roomId) => {
      const room = findEntity(payload.entities.rooms, roomId);
      return room ? { room_id: roomId, ...room } : null;
    })
    .filter((room): room is ExportRoomRelationChange => room !== null);
  const teacherDetails = (record.teacher_ids ?? [])
    .map((teacherId) => {
      const teacher = findEntity(payload.entities.teachers, teacherId);
      return teacher ? { teacher_id: teacherId, ...teacher } : null;
    })
    .filter((teacher): teacher is ExportTeacherRelationChange => teacher !== null);

  return {
    ...record,
    room_details: roomDetails.length ? roomDetails : record.room_details,
    teacher_details: teacherDetails.length ? teacherDetails : record.teacher_details,
  };
}

function normalizeEntityId(value: string): string {
  return value.replaceAll("-", "");
}

function findEntity<T>(entities: Record<string, T>, id: string): T | undefined {
  const exact = entities[id];
  if (exact !== undefined) return exact;

  const normalizedId = normalizeEntityId(id);
  const normalized = entities[normalizedId];
  if (normalized !== undefined) return normalized;

  return Object.entries(entities).find(([key]) => normalizeEntityId(key) === normalizedId)?.[1];
}

function sessionForStep(
  step: CompactProjectExportPayload["modification_steps"][number],
  payload: CompactProjectExportPayload,
): ExportModificationStep["session"] {
  const sessionId = step.session_ids[0] ?? "";
  return (
    findEntity(payload.entities.sessions, sessionId) ?? {
      id: sessionId,
      start_time: 0,
      duration: 0,
      weekday: "monday",
      week: "",
      rooms: [],
      teachers: [],
      classes: [],
      subjects: [],
    }
  );
}

function baseConflict(conflict: CompactProjectExportPayload["conflicts"][number]) {
  return {
    week: conflict[2],
    weeks: conflict[3],
    weekday: conflict[4],
    start_time: conflict[5],
    duration: conflict[6],
    collisions: conflict[7],
    session_ids: conflict[8],
    subject_labels: conflict[9] ?? [],
  };
}

function expandModifications(
  modifications: Record<string, unknown>,
  payload: CompactProjectExportPayload,
): ExportSessionModifications {
  const expanded: ExportSessionModifications = {};

  for (const [field, change] of Object.entries(modifications)) {
    if (!change) continue;

    if (field === "rooms") {
      expanded.rooms = expandRelationChange(
        change,
        "room_id",
        payload.entities.rooms,
      ) as unknown as ExportAddedRemovedRecords<ExportRoomRelationChange>;
    } else if (field === "teachers") {
      expanded.teachers = expandRelationChange(
        change,
        "teacher_id",
        payload.entities.teachers,
      ) as unknown as ExportAddedRemovedRecords<ExportTeacherRelationChange>;
    } else if (field === "class_subjects") {
      expanded.class_subjects = expandClassSubjectChange(change, payload);
    } else {
      expanded[field] = change as ExportFieldModification;
    }
  }

  return expanded;
}

function expandRelationChange<T extends object>(
  change: unknown,
  idKey: string,
  entities: Record<string, T>,
): ExportAddedRemovedRecords<T> {
  if (!isRelationChange(change)) return { added: [], removed: [] };

  return {
    added: change.added.map((record) => expandRelationRecord(record, idKey, entities)),
    removed: change.removed.map((record) => expandRelationRecord(record, idKey, entities)),
  };
}

function expandRelationRecord<T extends object>(
  record: unknown,
  idKey: string,
  entities: Record<string, T>,
): T {
  if (typeof record === "string") {
    return { [idKey]: record, ...(findEntity(entities, record) ?? {}) } as T;
  }

  if (typeof record !== "object" || record === null || !(idKey in record)) {
    return record as T;
  }

  const id = String((record as Record<string, unknown>)[idKey]);
  return { [idKey]: id, ...(findEntity(entities, id) ?? {}) } as T;
}

function expandClassSubjectChange(
  change: unknown,
  payload: CompactProjectExportPayload,
): ExportAddedRemovedRecords<ExportClassSubjectRelationChange> {
  if (!isRelationChange(change)) return { added: [], removed: [] };

  return {
    added: change.added.map((record) => expandClassSubjectRecord(record, payload)),
    removed: change.removed.map((record) => expandClassSubjectRecord(record, payload)),
  };
}

function expandClassSubjectRecord(
  record: unknown,
  payload: CompactProjectExportPayload,
): ExportClassSubjectRelationChange {
  if (Array.isArray(record) && record.length >= 2) {
    return expandClassSubjectIds(String(record[0]), String(record[1]), payload);
  }

  if (
    typeof record !== "object" ||
    record === null ||
    !("class_id" in record) ||
    !("subject_id" in record)
  ) {
    return record as ExportClassSubjectRelationChange;
  }

  const classId = String((record as Record<string, unknown>).class_id);
  const subjectId = String((record as Record<string, unknown>).subject_id);
  return expandClassSubjectIds(classId, subjectId, payload);
}

function expandClassSubjectIds(
  classId: string,
  subjectId: string,
  payload: CompactProjectExportPayload,
): ExportClassSubjectRelationChange {
  const classEntity = findEntity(payload.entities.classes, classId);
  return {
    class_id: classId,
    subject_id: subjectId,
    ...(classEntity
      ? {
          class_code: classEntity.class_code,
          class_shift: classEntity.class_shift,
        }
      : {}),
    ...findEntity(payload.entities.subjects, subjectId),
  };
}

function isRelationChange(change: unknown): change is {
  added: unknown[];
  removed: unknown[];
} {
  return typeof change === "object" && change !== null && "added" in change && "removed" in change;
}
