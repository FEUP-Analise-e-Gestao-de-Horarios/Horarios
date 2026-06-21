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

// -- Week blocks ---------------------------------------------------------
export interface WeekBlockResponse {
  weeks: string[];
  sessions: SessionResponse[];
}

export interface SessionsResponse {
  blocks: WeekBlockResponse[];
}
