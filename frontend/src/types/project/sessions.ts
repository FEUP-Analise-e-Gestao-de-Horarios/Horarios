import type { ClassBase } from "./class";
import type { RoomBase } from "./room";
import type { SubjectBase } from "./subject";
import type { TeacherBase } from "./teacher";
import type { Weekday } from "./weekday";

// -- Base ----------------------------------------------------------------
export interface SessionBase {
  id: string;
  original_block_id: string;
  week: string;
  weekday: Weekday;
  start_time: number;
  duration: number;
  type: string;
}

// -- Response ------------------------------------------------------------
export interface SessionResponse extends SessionBase {
  teachers: TeacherBase[];
  subjects: SubjectBase[];
  classes: ClassBase[];
  rooms: RoomBase[];
}

// -- Update (contract C1) --------------------------------------------------
/** PATCH body for /api/projects/<pid>/sessions/<sid>/ — send only changed fields. */
export interface SessionPatch {
  weekday?: Weekday;
  /** HHMM encoding, same as SessionBase.start_time. */
  start_time?: number;
  /** Duration in 30-minute slots, same as SessionBase.duration. */
  duration?: number;
  teacher_ids?: string[];
  room_ids?: string[];
  class_ids?: string[];
  subject_ids?: string[];
  /**
   * ISO date strings (a subset of the target session's `WeekGridEvent.weeks`).
   * The backend fans the same patch out to every session sharing the
   * target's `original_block_id` whose `week` is in this list, plus the
   * target itself — so moving a recurring class only affects the weeks
   * currently selected/filtered, not every week it has ever run. Omit or
   * leave empty to patch only the target session.
   */
  weeks?: string[];
}

// -- Week blocks ---------------------------------------------------------
export interface WeekBlockResponse {
  weeks: string[];
  sessions: SessionResponse[];
}

export interface SessionsResponse {
  blocks: WeekBlockResponse[];
}
