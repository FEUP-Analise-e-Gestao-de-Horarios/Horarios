import type {
  CompactProjectExportPayload,
  ExportAddedRemovedRecords,
  ExportClassConflict,
  ExportClassSubjectRelationChange,
  ExportFieldModification,
  ExportModificationStep,
  ExportRoomConflict,
  ExportRoomRelationChange,
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
  if (!isCompactExportPayload(payload)) return payload;

  return {
    added_removed_sessions: payload.added_removed_sessions,
    rooms_conflicts: payload.conflicts
      .filter((conflict) => conflict[0] === "room")
      .map((conflict): ExportRoomConflict => {
        const room = payload.entities.rooms[conflict[1]];
        return {
          ...baseConflict(conflict),
          room_id: conflict[1],
          room_name: room?.room_name ?? conflict[1],
        };
      }),
    teacher_conflicts: payload.conflicts
      .filter((conflict) => conflict[0] === "teacher")
      .map((conflict): ExportTeacherConflict => {
        const teacher = payload.entities.teachers[conflict[1]];
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
      .map(
        (conflict): ExportClassConflict => ({
          ...baseConflict(conflict),
          class_id: conflict[1],
          class_code: payload.entities.classes[conflict[1]]?.class_code ?? conflict[1],
        }),
      ),
    modification_steps: payload.modification_steps.map(
      (step): ExportModificationStep => ({
        ...step,
        session: payload.entities.sessions[step.session_ids[0] ?? ""] ?? {
          id: step.session_ids[0] ?? "",
          start_time: 0,
          duration: 0,
          weekday: "monday",
          week: "",
          rooms: [],
          teachers: [],
          classes: [],
          subjects: [],
        },
        modifications: expandModifications(step.modifications, payload),
      }),
    ),
  };
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
    return { [idKey]: record, ...(entities[record] ?? {}) } as T;
  }

  if (typeof record !== "object" || record === null || !(idKey in record)) {
    return record as T;
  }

  const id = String((record as Record<string, unknown>)[idKey]);
  return { [idKey]: id, ...(entities[id] ?? {}) } as T;
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
  return {
    class_id: classId,
    subject_id: subjectId,
    ...payload.entities.classes[classId],
    ...payload.entities.subjects[subjectId],
  };
}

function isRelationChange(change: unknown): change is {
  added: unknown[];
  removed: unknown[];
} {
  return typeof change === "object" && change !== null && "added" in change && "removed" in change;
}
