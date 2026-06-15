import type { RedBlockBase } from "./red_block";
import type { WeekBlockResponse } from "./sessions";
import type { YearBase } from "./year";

// -- Base ----------------------------------------------------------------
export interface ClassBase {
  id: string;
  year_id: string;
  code: string;
  shift: number;
}

export interface ClassWithSessions extends ClassBase {
  sessions: number;
}

// -- Detail --------------------------------------------------------------
export interface ClassDetail extends ClassBase {
  year: YearBase;
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}
