import type { ClassBase } from "./class";
import type { RedBlockBase } from "./red_block";
import type { WeekBlockResponse } from "./sessions";
import type { SubjectBase } from "./subject";

// -- Base ----------------------------------------------------------------
export interface TeacherBase {
  id: string;
  number: number;
  acronym: string;
  name: string;
}

// -- List payload --------------------------------------------------------
export interface TeachersListPayload {
  teachers: TeacherStats[];
  count: number;
}

// -- Stats ---------------------------------------------------------------
export interface TeacherStats extends TeacherBase {
  subjects: number;
  classes: number;
  sessions: number;
  red_blocks: number;
}

// -- Detail --------------------------------------------------------------
export interface TeacherDetail extends TeacherBase {
  subjects: SubjectBase[];
  classes: ClassBase[];
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}
