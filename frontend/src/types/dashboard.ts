export interface ProjectStats {
  degrees: number;
  years: number;
  subjects: number;
  classes: number;
  teachers: number;
  rooms: number;
  sessions: number;
}

export type Weekday = "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday";

// ---------------------------------------------------------------------------
// Simple entity bases (mirror backend *Base — all DB attributes)
// ---------------------------------------------------------------------------

export interface ClassBase {
  id: string;
  year_id: string;
  code: string;
  shift: number;
}

export interface DegreeBase {
  id: string;
  acronym: string;
  name: string;
}

export interface RedBlockBase {
  id: string;
  hour: number;
  weekday: Weekday;
}

export interface RoomBase {
  id: string;
  name: string;
  type: string | null;
  size: string | null;
  seats: string | null;
}

export interface SubjectBase {
  id: string;
  year_id: string;
  number: number;
  code: string;
  acronym: string;
  name: string;
}

export interface TeacherBase {
  id: string;
  number: number;
  acronym: string;
  name: string;
}

export interface YearBase {
  id: string;
  degree_id: string;
  number: number;
}

export interface SubjectWithSessions extends SubjectBase {
  sessions: number;
}

export interface ClassWithSessions extends ClassBase {
  sessions: number;
}

export interface SessionBase {
  id: string;
  original_block_id: string;
  week: string;
  weekday: Weekday;
  start_time: number;
  duration: number;
  type: string;
}

// ---------------------------------------------------------------------------
// Session response (enriched with nested lists)
// ---------------------------------------------------------------------------

export interface SessionResponse extends SessionBase {
  teachers: TeacherBase[];
  subjects: SubjectBase[];
  classes: ClassBase[];
  rooms: RoomBase[];
}

// ---------------------------------------------------------------------------
// Week blocks (contiguous weeks with identical timetables)
// ---------------------------------------------------------------------------

export interface WeekBlockResponse {
  weeks: string[];
  sessions: SessionResponse[];
}

export interface SessionsResponse {
  blocks: WeekBlockResponse[];
}

export interface ConflictRecord {
  id: string;
  event_ids: string[];
  event_names: string[];
  day: string;
  time: string;
  turma: string;
  conflict_reasons: string[];
}

// ---------------------------------------------------------------------------
// Listing (stats) responses
// ---------------------------------------------------------------------------

export interface DegreeStats extends DegreeBase {
  years: number;
  subjects: number;
  classes: number;
  sessions: number;
}

export interface TeacherStats extends TeacherBase {
  subjects: number;
  classes: number;
  sessions: number;
  red_blocks: number;
}

export interface RoomStats extends RoomBase {
  sessions: number;
  red_blocks: number;
}

export interface SubjectStats extends SubjectBase {
  degree_id: string;
  degree_acronym: string;
  degree_name: string;
  year_id: string;
  year_number: number;
  sessions: number;
}

// ---------------------------------------------------------------------------
// Detail responses
// ---------------------------------------------------------------------------

export interface TeacherDetail extends TeacherBase {
  subjects: SubjectBase[];
  classes: ClassBase[];
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}

export interface RoomDetail extends RoomBase {
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}

export interface YearDetail extends YearBase {
  subjects: SubjectWithSessions[];
  classes: ClassWithSessions[];
}

export interface DegreeYearStats extends YearBase {
  subjects: number;
  classes: number;
  sessions: number;
}

export interface DegreeDetail extends DegreeBase {
  years: DegreeYearStats[];
}

export interface SubjectDetail extends SubjectBase {
  year: YearBase;
  blocks: WeekBlockResponse[];
}

export interface ClassDetail extends ClassBase {
  year: YearBase;
  blocks: WeekBlockResponse[];
}

// ---------------------------------------------------------------------------
// List payloads (shape inside ApiResponse<T> for collection endpoints)
// ---------------------------------------------------------------------------

export interface DegreesListPayload {
  degrees: DegreeStats[];
  count: number;
}

export interface TeachersListPayload {
  teachers: TeacherStats[];
  count: number;
}

export interface RoomsListPayload {
  rooms: RoomStats[];
  count: number;
}

export interface SubjectsListPayload {
  subjects: SubjectStats[];
  count: number;
}

export interface ConflictsListPayload {
  conflicts: ConflictRecord[];
  count: number;
}
