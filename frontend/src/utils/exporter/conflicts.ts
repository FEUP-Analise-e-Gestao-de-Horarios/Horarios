import type {
  ExportConflictBase,
  ExportTeacherConflict,
  ProjectExportPayload,
} from "@/types/exporter";
import { anchorPart, normalizeId } from "@/utils/exporter/ids";

export type ConflictKind = "room" | "teacher" | "class";

export interface ConflictTarget {
  anchor: string;
  label: string;
  kind: ConflictKind;
}

export type ConflictLookup = Record<string, ConflictTarget>;

export function conflictCardAnchorId(
  kind: ConflictKind,
  row: ExportConflictBase,
  index: number,
): string {
  return [
    "export-conflict",
    kind,
    anchorPart(row.week),
    anchorPart(row.weekday),
    row.start_time,
    index,
  ].join("-");
}

export function conflictAulasCount(row: ExportConflictBase): number {
  const uniqueSessions = new Set(row.session_ids.map(normalizeId)).size;
  const weekCount = row.weeks?.length ?? 1;
  return Math.max(1, Math.round(uniqueSessions / weekCount));
}

export function teacherConflictName(row: ExportTeacherConflict): string {
  if (row.teacher_acronym.trim() === row.teacher_name.trim()) return row.teacher_acronym;
  return `${row.teacher_acronym} · ${row.teacher_name}`;
}

export function buildConflictSessionIds(data: ProjectExportPayload): Set<string> {
  return new Set(
    [...data.rooms_conflicts, ...data.teacher_conflicts, ...data.classes_conflicts].flatMap(
      (conflict) => conflict.session_ids.map((sessionId) => normalizeId(sessionId)),
    ),
  );
}

export function buildConflictLookup(data: ProjectExportPayload): ConflictLookup {
  const lookup: ConflictLookup = {};

  function addConflict(kind: ConflictKind, row: ExportConflictBase, index: number, label: string) {
    const anchor = conflictCardAnchorId(kind, row, index);
    for (const sessionId of row.session_ids) {
      lookup[normalizeId(sessionId)] ??= { anchor, label, kind };
    }
  }

  data.rooms_conflicts.forEach((row, index) => {
    addConflict("room", row, index, `Sala ${row.room_name}`);
  });
  data.teacher_conflicts.forEach((row, index) => {
    addConflict("teacher", row, index, `Docente ${row.teacher_acronym}`);
  });
  data.classes_conflicts.forEach((row, index) => {
    addConflict("class", row, index, `Turma ${row.class_code}`);
  });

  return lookup;
}
