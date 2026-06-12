import type { Weekday } from "./weekday";

// -- Parallel-class restrictions (contract C4) -------------------------------
/** A slot blocked because a parallel session of the same UC occupies it. */
export interface ParallelBlock {
  weekday: Weekday;
  /** Start of the blocked slot, HHMM encoding (e.g. 1030). */
  hour: number;
  source: {
    degree_acronym: string;
    class_code: string;
    session_id: string;
  };
}

export interface ParallelBlocksPayload {
  blocks: ParallelBlock[];
}
