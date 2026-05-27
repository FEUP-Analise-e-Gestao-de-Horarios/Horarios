export type UUID = string;

export interface YearOption {
  id: UUID;
  number: number;
}

export interface DegreeOption {
  id: UUID;
  name: string;
  acronym: string;
}

export interface ParallelCandidateSession {
  original_block_id: UUID;
  class_codes: string[];
  session_type: string;
}

export interface ParallelCandidate {
  candidate_group_id: UUID;
  subject_name: string;
  session_start_time: number;
  session_weekday: string;
  session_duration: number;
  session_week: string;
  sessions: ParallelCandidateSession[];
  year: number;
  degree_id: string;
  degree_acronym: string;
}

export interface SuccessResponse<T> {
  message: string;
  data: T;
}

export interface LocalGroup {
  id: string;
  blockIds: UUID[];
}

export interface BlockMeta {
  subject_name: string;
  weekday: string;
  start_time: number;
  class_codes: string[];
  session_type?: string;
  session_week?: string;
}

export interface DisplayCandidate extends ParallelCandidate {
  showWeek: boolean;
  displayWeeks: string[];
  equivalentCandidates: ParallelCandidate[];
}

export interface EnrichedGroup {
  group: LocalGroup;
  subject_name: string;
  weekday: string;
  start_time: number;
  session_week: string | undefined;
  sessions: BlockMeta[];
}

export const DAY_ORDER: Record<string, number> = {
  monday: 0,
  tuesday: 1,
  wednesday: 2,
  thursday: 3,
  friday: 4,
};
