import type { Weekday } from "@/types/dashboard";

export type ExportModificationStepType = "move" | "exchange";

export type ExportPrimitive = string | number | boolean | null;
export type ExportJsonValue =
  | ExportPrimitive
  | ExportJsonValue[]
  | { [key: string]: ExportJsonValue };

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
  room: string;
}

export interface ExportTeacherRelationChange {
  teacher_id: string;
  teacher: string;
}

export interface ExportClassSubjectRelationChange {
  class_id: string;
  class: string;
  subject_id: string;
  subject: string;
}

export type ExportFieldModification =
  | ExportColumnChange<unknown>
  | ExportAddedRemovedRecords<unknown>;

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
  code: string;
}

export interface ExportModificationSession {
  modifications: ExportSessionModifications;
  dependencies: string[];
  session: ExportSessionSnapshot;
}

export interface ExportModificationStep {
  type: ExportModificationStepType;
  sessions: Record<string, ExportModificationSession>;
}

export type ExportModificationSteps = ExportModificationStep[];

export interface ExportConflictBase {
  week: string;
  weekday: Weekday;
  start_time: number;
  duration: number;
  collisions: number;
  session_ids: string[];
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
