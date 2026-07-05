import type { ClassWithSessions } from "./class";
import type { DegreeBase } from "./degree";
import type { SubjectWithSessions } from "./subject";

// -- Base ----------------------------------------------------------------
export interface YearBase {
  id: string;
  degree_id: string;
  number: number;
}

// -- With degree ---------------------------------------------------------
export interface YearWithDegree extends YearBase {
  degree: DegreeBase;
}

// -- Detail --------------------------------------------------------------
export interface YearDetail extends YearBase {
  subjects: SubjectWithSessions[];
  classes: ClassWithSessions[];
}
