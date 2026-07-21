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

// -- Split -----------------------------------------------------------------
/**
 * POST body for /api/projects/<pid>/sessions/<sid>/split/ — detaches
 * `class_ids` (a non-empty, proper subset of the session's current classes)
 * into a brand new session at the given slot. The target session keeps its
 * other classes untouched, so a class removed from the middle of a
 * contiguous turma span leaves a gap the grid renders as two segments of
 * the same session, connected by its existing same-session arc — nothing
 * extra to draw.
 */
export interface SessionSplit {
  class_ids: string[];
  /**
   * Classes the new session actually teaches; defaults to `class_ids` when
   * omitted (the detached slot keeps teaching the same class, just at a new
   * slot). Set differently to reassign the detached slot to a *different*
   * turma in the same move — same as moving a plain single-turma event to a
   * different turma column, but for one turma of a shared session.
   */
  new_class_ids?: string[];
  weekday: Weekday;
  /** HHMM encoding, same as SessionBase.start_time. */
  start_time: number;
  /** Duration in 30-minute slots, same as SessionBase.duration. */
  duration: number;
  /** Defaults to the target session's own teachers/rooms when omitted. */
  teacher_ids?: string[];
  room_ids?: string[];
  /** Required when the detached classes don't all share one subject. */
  subject_ids?: string[];
  /** Same fan-out semantics as SessionPatch.weeks. */
  weeks?: string[];
}

export interface SessionSplitResult {
  original: SessionResponse;
  created: SessionResponse;
}

// -- Week blocks ---------------------------------------------------------
export interface WeekBlockResponse {
  weeks: string[];
  sessions: SessionResponse[];
}

export interface SessionsResponse {
  blocks: WeekBlockResponse[];
}
