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
  type: string;
  size: string;
  seats: string;
  sessions: number;
  red_blocks: number;
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
