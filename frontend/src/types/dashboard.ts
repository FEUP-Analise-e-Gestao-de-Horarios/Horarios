export interface ProjectStats {
  degrees: number;
  years: number;
  subjects: number;
  classes: number;
  teachers: number;
  rooms: number;
  sessions: number;
}

export interface DegreeStats {
  id: string;
  acronym: string;
  name: string;
  years: number;
  subjects: number;
  classes: number;
  sessions: number;
}

export interface TeacherStats {
  id: string;
  number: number;
  acronym: string;
  name: string;
  subjects: number;
  classes: number;
  sessions: number;
}

export interface RoomStats {
  id: string;
  name: string;
  type: string | null;
  size: string | null;
  seats: string | null;
  sessions: number;
  red_blocks: number;
}

export interface SubjectDetail {
  id: string;
  year_id: string;
  number: number;
  code: string;
  acronym: string;
  name: string;
}

export interface ClassDetail {
  id: string;
  year_id: string;
  code: string;
  shift: number;
}

export interface SessionDetail {
  id: string;
  original_block_id: string;
  week: string;
  weekday: string;
  start_time: number;
  duration: number;
  type: string;
}

export interface RedBlockDetail {
  id: string;
  hour: number;
  weekday: string;
}

export interface TeacherDetail {
  id: string;
  number: number;
  acronym: string;
  name: string;
  subjects: SubjectDetail[];
  classes: ClassDetail[];
  sessions: SessionDetail[];
}

export interface RoomDetail {
  id: string;
  name: string;
  type: string | null;
  size: string | null;
  seats: string | null;
  sessions: SessionDetail[];
  red_blocks: RedBlockDetail[];
}

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
  data: DegreeStats;
}

export interface TeacherDetailApiResponse {
  data: TeacherDetail;
}

export interface RoomDetailApiResponse {
  data: RoomDetail;
}
