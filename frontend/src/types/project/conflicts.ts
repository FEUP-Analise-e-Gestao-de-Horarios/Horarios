// -- Base ----------------------------------------------------------------
export interface ConflictRecord {
  id: string;
  event_ids: string[];
  event_names: string[];
  day: string;
  time: number;
  turma: string[];
  block_ids: string[];
  degrees: string[];
  subjects: string[];
  conflict_reasons: string[];
  tags: string[];
}

// -- Tag constants -------------------------------------------------------
export const CONFLICT_TAGS = {
  PRE_EXISTING: "pre-existing",
  IGNORED: "ignored",
} as const;

// -- List payload --------------------------------------------------------
export interface ConflictsListPayload {
  conflicts: ConflictRecord[];
  count: number;
}

// -- Many tag update -----------------------------------------------------
export interface UpdateManyConflictTagItem {
  conflict_id: string;
  tags: string[];
}

export interface UpdateManyConflictTagsRequest {
  updates: UpdateManyConflictTagItem[];
}

export interface UpdateManyConflictTagsResponse {
  conflicts: ConflictRecord[];
}

// -- Preview -------------------------------------------------------------
export interface ConflictPreviewRequest {
  original_block_id: string;
  weekday: string;
  start_time: number;
  duration: number;
  teacher_ids: string[];
  room_ids: string[];
  class_ids: string[];
}

export interface ConflictPreviewResponse {
  solved: ConflictRecord[];
  new: ConflictRecord[];
}
