export type UUID = string;

// -- Wire shape (GET /parallel-blocks/candidates) ------------------------
// Each candidate group is a connected component of the week-overlap graph:
// `nodes` are the blocks, `edges` are the undirected adjacency pairs of
// blocks that collide on at least one week. A valid selection is a connected
// subgraph of these edges.

export interface ParallelSessionTemplate {
  type: string;
  start_time: number;
  duration: number;
}

export interface ParallelBlockClass {
  id: UUID;
  code: string;
  /** The `subject.years` row this class belongs to (resolve degree there). */
  year_id: UUID;
}

export interface ParallelBlockNode {
  original_block_id: UUID;
  /** The confirmed parallel group this block is already saved under, if any. */
  confirmed_group_id: UUID | null;
  first_week: string;
  last_week: string;
  session: ParallelSessionTemplate;
  classes: ParallelBlockClass[];
}

export interface ParallelDegree {
  id: UUID;
  acronym: string;
  name: string;
}

export interface ParallelYear {
  id: UUID;
  degree: ParallelDegree;
}

export interface ParallelSubject {
  id: UUID;
  acronym: string;
  name: string;
  /** Only the year/degree combinations present in this group. */
  years: ParallelYear[];
}

// An undirected adjacency between two blocks. `source`/`target` are the two
// blocks' ids (order carries no meaning); `weeks` lists every week on which the
// blocks collide (ISO dates).
export interface ParallelCandidateEdge {
  source: UUID;
  target: UUID;
  weeks: string[];
}

export interface ParallelCandidateGraph {
  candidate_group_id: UUID;
  weekday: string;
  subject: ParallelSubject;
  nodes: ParallelBlockNode[];
  edges: ParallelCandidateEdge[];
}

export interface SuccessResponse<T> {
  message: string;
  data: T;
}

// -- Filter options (derived client-side) --------------------------------
export interface DegreeOption {
  id: UUID;
  name: string;
  acronym: string;
}

export interface YearOption {
  id: UUID;
  number: number;
}

// -- Local selection model ----------------------------------------------
/** A group the user has formed (or one loaded from the server). */
export interface ParallelGroup {
  /** Local id; for server-loaded groups this is the confirmed_group_id. */
  id: string;
  candidateGroupId: UUID;
  blockIds: UUID[];
  /** True when this group is already persisted on the server. */
  confirmed: boolean;
}

export const DAY_ORDER: Record<string, number> = {
  monday: 0,
  tuesday: 1,
  wednesday: 2,
  thursday: 3,
  friday: 4,
  saturday: 5,
};
