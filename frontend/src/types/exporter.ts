import type { Weekday } from "@/types/project/weekday";

export type ExportModificationStepType = "move" | "exchange";

export type ExportPrimitive = string | number | boolean | null;
export type ExportJsonValue =
  ExportPrimitive | ExportJsonValue[] | { [key: string]: ExportJsonValue };

export interface ExportColumnChange<T = ExportJsonValue> {
  old: T;
  new: T;
}

export interface ExportAddedRemovedRecords<T = ExportJsonValue> {
  added: T[];
  removed: T[];
}

export interface ExportSessionRecord {
  id: string;
}

export interface ExportRoomRelationChange {
  room_id: string;
  room_name?: string;
  room_type?: string | null;
  room_size?: string | null;
  room_seats?: string | null;
}

export interface ExportTeacherRelationChange {
  teacher_id: string;
  teacher_number?: number;
  teacher_acronym?: string;
  teacher_name?: string;
}

export interface ExportClassSubjectRelationChange {
  class_id: string;
  class_code?: string;
  class_shift?: number;
  subject_id: string;
  subject_number?: number;
  subject_code?: string;
  subject_acronym?: string;
  subject_name?: string;
}

export type ExportFieldModification =
  ExportColumnChange<unknown> | ExportAddedRemovedRecords<unknown>;

export interface ExportSessionModifications {
  start_time?: ExportColumnChange<number>;
  duration?: ExportColumnChange<number>;
  weekday?: ExportColumnChange<Weekday>;
  week?: ExportColumnChange<string>;
  type?: ExportColumnChange<string>;
  original_block_id?: ExportColumnChange<string>;
  rooms?: ExportAddedRemovedRecords<ExportRoomRelationChange>;
  teachers?: ExportAddedRemovedRecords<ExportTeacherRelationChange>;
  class_subjects?: ExportAddedRemovedRecords<ExportClassSubjectRelationChange>;
  [field: string]: ExportFieldModification | undefined;
}

export interface ExportSessionSnapshot {
  id: string;
  original_block_id?: string;
  start_time: number;
  duration: number;
  weekday: Weekday;
  week: string;
  rooms: string[];
  teachers: ExportTeacherSnapshot[];
  classes: string[];
  subjects: ExportSubjectsSnapshot[];
}

export interface ExportTeacherSnapshot {
  number: number;
  name: string;
  acronym: string;
}

export interface ExportSubjectsSnapshot {
  name: string;
  acronym?: string;
  code: string;
}

export interface ExportWeekRange {
  start: string | null;
  end: string | null;
  contiguous: boolean;
}

export interface ExportModificationStep {
  type: ExportModificationStepType;
  original_block_id: string;
  session_ids: string[];
  weeks: string[];
  week_range: ExportWeekRange;
  applies_to_all_weeks?: boolean;
  modifications: ExportSessionModifications;
  dependencies: string[];
  session: ExportSessionSnapshot;
}

export type ExportModificationSteps = ExportModificationStep[];

export interface ExportConflictBase {
  week: string;
  weeks?: string[];
  weekday: Weekday;
  start_time: number;
  duration: number;
  collisions: number;
  session_ids: string[];
  subject_labels?: string[];
}

export interface ExportRoomConflict extends ExportConflictBase {
  room_id: string;
  room_name: string;
}

export interface ExportTeacherConflict extends ExportConflictBase {
  teacher_id: string;
  teacher_number: number;
  teacher_acronym: string;
  teacher_name: string;
}

export interface ExportClassConflict extends ExportConflictBase {
  class_id: string;
  class_code: string;
}

export interface ProjectExportPayload {
  added_removed_sessions: ExportAddedRemovedRecords<ExportSessionRecord>;
  rooms_conflicts: ExportRoomConflict[];
  teacher_conflicts: ExportTeacherConflict[];
  classes_conflicts: ExportClassConflict[];
  modification_steps: ExportModificationSteps;
}

export type CompactExportConflictKind = "room" | "teacher" | "class";

export type CompactExportConflict = [
  kind: CompactExportConflictKind,
  resourceId: string,
  week: string,
  weeks: string[] | undefined,
  weekday: Weekday,
  startTime: number,
  duration: number,
  collisions: number,
  sessionIds: string[],
  subjectLabels?: string[],
];

export interface CompactExportEntities {
  rooms: Record<string, Omit<ExportRoomRelationChange, "room_id">>;
  teachers: Record<string, Omit<ExportTeacherRelationChange, "teacher_id">>;
  classes: Record<string, Pick<ExportClassSubjectRelationChange, "class_code" | "class_shift">>;
  subjects: Record<
    string,
    Pick<
      ExportClassSubjectRelationChange,
      "subject_number" | "subject_code" | "subject_acronym" | "subject_name"
    >
  >;
  sessions: Record<string, ExportSessionSnapshot>;
}

export interface CompactExportModificationStep extends Omit<
  ExportModificationStep,
  "session" | "modifications"
> {
  modifications: Record<string, unknown>;
}

export interface CompactProjectExportPayload {
  format: "compact_export_v1";
  entities: CompactExportEntities;
  added_removed_sessions: ExportAddedRemovedRecords<ExportSessionRecord>;
  conflicts: CompactExportConflict[];
  modification_steps: CompactExportModificationStep[];
}

export type ProjectExportApiPayload = ProjectExportPayload | CompactProjectExportPayload;
