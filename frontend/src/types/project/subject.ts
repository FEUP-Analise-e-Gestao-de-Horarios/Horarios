import type { WeekBlockResponse } from "./sessions";
import type { YearWithDegree } from "./year";

// -- Base ----------------------------------------------------------------
export interface SubjectBase {
  id: string;
  number: number;
  code: string;
  acronym: string;
  name: string;
}

// -- List payload --------------------------------------------------------
export interface SubjectsListPayload {
  subjects: SubjectStats[];
  count: number;
}

// -- Stats ---------------------------------------------------------------
export interface SubjectStats extends SubjectBase {
  sessions: number;
}

// -- Detail --------------------------------------------------------------
export interface SubjectDetail extends SubjectBase {
  years: YearWithDegree[];
  blocks: WeekBlockResponse[];
}

// -- Nested --------------------------------------------------------------
export interface SubjectWithSessions extends SubjectBase {
  sessions: number;
}
