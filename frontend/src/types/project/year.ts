import type { ClassWithSessions } from "./class";
import type { SubjectWithSessions } from "./subject";

// -- Base ----------------------------------------------------------------
export interface YearBase {
  id: string;
  degree_id: string;
  number: number;
}

// -- Detail --------------------------------------------------------------
export interface YearDetail extends YearBase {
  subjects: SubjectWithSessions[];
  classes: ClassWithSessions[];
}
