// -- Base ----------------------------------------------------------------
export interface ConflictRecord {
  id: string;
  /** Bare session ids (contract C2) — matched against WeekGridEvent.sessionId. */
  event_ids: string[];
  event_names: string[];
  day: string;
  time: string;
  turma: string;
  conflict_reasons: string[];
  degree_id: string;
  year_id: string;
  ignored: boolean;
}

/** Which slice of conflicts to fetch (contract C2 `scope` query param). */
export type ConflictScope = "year" | "mine" | "all";

// -- List payload --------------------------------------------------------
export interface ConflictsListPayload {
  conflicts: ConflictRecord[];
  count: number;
}

// -- Ignore (contract C3) --------------------------------------------------
export interface ConflictIgnoredResult {
  id: string;
  ignored: boolean;
}
