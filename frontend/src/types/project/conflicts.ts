// -- Base ----------------------------------------------------------------
export interface ConflictRecord {
  id: string;
  event_ids: string[];
  event_names: string[];
  day: string;
  time: string;
  turma: string;
  conflict_reasons: string[];
}

// -- List payload --------------------------------------------------------
export interface ConflictsListPayload {
  conflicts: ConflictRecord[];
  count: number;
}
