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
}

export interface RoomStats extends RoomBase {
  sessions: number;
  red_blocks: number;
}

// ---------------------------------------------------------------------------
// Detail responses
// ---------------------------------------------------------------------------

export interface TeacherDetail extends TeacherBase {
  subjects: SubjectBase[];
  classes: ClassBase[];
  blocks: WeekBlockResponse[];
}

export interface RoomDetail extends RoomBase {
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}

export interface YearDetail extends YearBase {
  subjects: SubjectWithSessions[];
  classes: ClassWithSessions[];
}

export interface DegreeDetail extends DegreeBase {
  years: YearDetail[];
}

// ---------------------------------------------------------------------------
// API envelopes
// ---------------------------------------------------------------------------

export interface StatsApiResponse {
  data: ProjectStats;
}

export interface DegreesApiResponse {
  data: { degrees: DegreeStats[]; count: number };
}

export interface TeachersApiResponse {
  data: { teachers: TeacherStats[]; count: number };
}

export interface RoomsApiResponse {
  data: { rooms: RoomStats[]; count: number };
}

export interface DegreeDetailApiResponse {
  data: DegreeDetail;
}

export interface TeacherDetailApiResponse {
  data: TeacherDetail;
}

export interface RoomDetailApiResponse {
  data: RoomDetail;
}
