import type {
  ConflictIgnoredResult,
  ConflictRecord,
  ConflictScope,
  ConflictsListPayload,
} from "@/types/project/conflicts";

/**
 * In-memory stand-ins for the backend endpoints that don't exist yet
 * (contracts C2/C3). Hooks route here while the matching flag in
 * `@/config/featureFlags` is off. Once the real endpoint ships, nothing in
 * this module is referenced for that feature and it can be deleted piecemeal.
 */

// -- Conflicts (C2/C3) -------------------------------------------------------

type ConflictSeed = Omit<ConflictRecord, "ignored" | "year_id"> & {
  /** Which scopes surface this seed; "year" seeds adopt the caller's yearId. */
  scopes: ConflictScope[];
};

// Placeholder records: real session ids are unknowable statically, so cards
// built from these won't match grid events — good enough to exercise drawer
// layout, scope tabs and the ignore flow until contract C2 lands.
const CONFLICT_SEEDS: ConflictSeed[] = [
  {
    id: "mock-cf-1",
    event_ids: ["mock-session-a", "mock-session-b"],
    event_names: ["IPC TP1", "BD PL3"],
    day: "Segunda-feira",
    time: "10:30",
    turma: "2LEIC01",
    conflict_reasons: ["Docente sobreposto: JSF"],
    degree_id: "mock-degree-leic",
    scopes: ["year", "mine", "all"],
  },
  {
    id: "mock-cf-2",
    event_ids: ["mock-session-c", "mock-session-d"],
    event_names: ["AED P2", "FSO P1"],
    day: "Quarta-feira",
    time: "14:00",
    turma: "2LEIC05",
    conflict_reasons: ["Sala sobreposta: B003", "Sala indisponível neste horário"],
    degree_id: "mock-degree-leic",
    scopes: ["year", "mine", "all"],
  },
  {
    id: "mock-cf-3",
    event_ids: ["mock-session-e"],
    event_names: ["SDIS T1"],
    day: "Sexta-feira",
    time: "08:30",
    turma: "1MEIC02",
    conflict_reasons: ["Docente indisponível neste horário"],
    degree_id: "mock-degree-meic",
    scopes: ["all"],
  },
];

const ignoredConflictIds = new Set<string>();

export function mockConflicts(
  scope: ConflictScope,
  opts: { yearId?: string; includeIgnored?: boolean } = {},
): ConflictsListPayload {
  const { yearId = "", includeIgnored = false } = opts;
  const conflicts = CONFLICT_SEEDS.filter((seed) => seed.scopes.includes(scope))
    .map((seed) => ({
      id: seed.id,
      event_ids: seed.event_ids,
      event_names: seed.event_names,
      day: seed.day,
      time: seed.time,
      turma: seed.turma,
      conflict_reasons: seed.conflict_reasons,
      degree_id: seed.degree_id,
      year_id: yearId,
      ignored: ignoredConflictIds.has(seed.id),
    }))
    .filter((conflict) => includeIgnored || !conflict.ignored);
  return { conflicts, count: conflicts.length };
}

export function mockSetConflictIgnored(
  conflictId: string,
  ignored: boolean,
): ConflictIgnoredResult {
  if (ignored) {
    ignoredConflictIds.add(conflictId);
  } else {
    ignoredConflictIds.delete(conflictId);
  }
  return { id: conflictId, ignored };
}

/** Test helper: reset the in-memory ignore state. */
export function mockResetIgnoredConflicts(): void {
  ignoredConflictIds.clear();
}
