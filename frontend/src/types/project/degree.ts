import type { YearBase } from "./year";

// -- Base ----------------------------------------------------------------
export interface DegreeBase {
  id: string;
  acronym: string;
  name: string;
}

// -- Stats ---------------------------------------------------------------
export interface DegreeStats extends DegreeBase {
  years: number;
  subjects: number;
  classes: number;
  sessions: number;
}

// -- List payload --------------------------------------------------------
export interface DegreesListPayload {
  degrees: DegreeStats[];
  count: number;
}

// -- Year stats ----------------------------------------------------------
export interface DegreeYearStats extends YearBase {
  subjects: number;
  classes: number;
  sessions: number;
}

// -- Detail --------------------------------------------------------------
export interface DegreeDetail extends DegreeBase {
  years: DegreeYearStats[];
}
