import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import type { SessionResponse } from "@/types/project/sessions";

/** Course group buckets, in display order. */
export const COURSE_GROUPS = [
  "Licenciaturas",
  "Mestrados",
  "Doutoramentos",
  "Pós-Graduações",
  "Outros",
] as const;

export type CourseGroupLabel = (typeof COURSE_GROUPS)[number];

/**
 * Pinned display order of the informática degrees inside each group (PI ToDo
 * #15). Acronyms not listed here sort alphabetically after the pinned ones —
 * the explicit list only makes sense while the app targets DEI; scaling to
 * the whole faculty should switch to permission-based ordering.
 */
export const COURSE_ACRONYM_ORDER: Partial<Record<CourseGroupLabel, string[]>> = {
  Licenciaturas: ["LEIC", "CINF"],
  Mestrados: ["MEIC", "MIA", "MESW", "MECD", "MCI", "MM"],
  Doutoramentos: ["PRODEI"],
};

// The backend serves sigarra acronyms with separators ("L.EIC", "M.IA");
// stripping non-alphanumerics lets them match the plain pinned forms.
function normalizeAcronym(acronym: string): string {
  return acronym.replace(/[^a-z0-9]/gi, "").toUpperCase();
}

/**
 * Comparator for degree acronyms within a course group: pinned acronyms first
 * in their listed order, everything else alphabetical after them. Matching is
 * separator-insensitive, so "L.EIC" hits the pinned "LEIC".
 */
export function compareCourseAcronyms(
  group: CourseGroupLabel,
): (left: string, right: string) => number {
  const pinned = COURSE_ACRONYM_ORDER[group] ?? [];
  const pinnedIndex = new Map(pinned.map((acronym, index) => [normalizeAcronym(acronym), index]));
  return (left, right) => {
    const leftIndex = pinnedIndex.get(normalizeAcronym(left)) ?? Number.POSITIVE_INFINITY;
    const rightIndex = pinnedIndex.get(normalizeAcronym(right)) ?? Number.POSITIVE_INFINITY;
    if (leftIndex !== rightIndex) return leftIndex - rightIndex;
    return left.localeCompare(right);
  };
}

/** The active schedule filters, pre-built into sets for fast membership tests. */
export type ScheduleFilters = {
  ucs: Set<string>;
  turnos: Set<string>;
  turmas: Set<string>;
  dias: Set<string>;
};

/**
 * Returns `values` de-duplicated, restricted to entries present in `reference`,
 * and sorted by their position in `reference`.
 */
export function sortValuesByReference(values: string[], reference: string[]): string[] {
  const referenceIndex = new Map(reference.map((value, index) => [value, index]));
  return [...new Set(values)]
    .filter((value) => referenceIndex.has(value))
    .sort((left, right) => (referenceIndex.get(left) ?? 0) - (referenceIndex.get(right) ?? 0));
}

/** Buckets a degree into one of the COURSE_GROUPS by name heuristics. */
export function getCourseGroupLabel(name: string): CourseGroupLabel {
  const normalized = name.toLowerCase();
  if (normalized.includes("licenciatura")) return "Licenciaturas";
  if (normalized.includes("mestrado")) return "Mestrados";
  if (normalized.includes("doutoramento") || normalized.includes("programa doutoral")) {
    return "Doutoramentos";
  }
  if (normalized.includes("pós") || normalized.includes("pos") || normalized.includes("gradua")) {
    return "Pós-Graduações";
  }
  return "Outros";
}

/** Fields shared by every WeekGridEvent derived from a given session. */
function buildBaseEvent(
  session: SessionResponse,
  blockWeeks: string[],
): Omit<WeekGridEvent, "id" | "turma"> {
  const primarySubject = session.subjects[0];
  const title = session.subjects.map((subject) => subject.acronym).join(", ") || session.type;
  const body = [
    session.teachers.map((teacher) => teacher.acronym).join(", "),
    session.rooms.map((room) => room.name).join(", "),
  ].filter((item) => item.length > 0);

  return {
    sessionId: session.id,
    weekday: session.weekday,
    startTime: session.start_time,
    duration: session.duration,
    title,
    body,
    type: session.type,
    classCodes: session.classes.map((classItem) => classItem.code),
    weeks: blockWeeks,
    uc: primarySubject?.name ?? primarySubject?.acronym ?? session.type,
    professor: session.teachers[0]?.acronym,
    sala: session.rooms[0]?.name,
    teachers: session.teachers.map((teacher) => ({
      id: teacher.id,
      acronym: teacher.acronym,
      name: teacher.name,
    })),
    rooms: session.rooms.map((room) => ({ id: room.id, name: room.name })),
    subjectNames: session.subjects.map((subject) => subject.name),
  };
}

/**
 * Flattens a backend session into the WeekGridEvent(s) that pass `filters`.
 * A session with classes expands to one event per matching class code; a
 * session with no classes yields a single event (and is hidden entirely once
 * any turma/turno filter is active). `blockWeeks` is the week list of the
 * containing week-block, stamped onto every event so the grid can tell which
 * weeks the session covers.
 */
export function sessionToEvents(
  session: SessionResponse,
  filters: ScheduleFilters,
  blockWeeks: string[] = [],
): WeekGridEvent[] {
  const { ucs, turnos, turmas, dias } = filters;

  if (ucs.size > 0 && !session.subjects.some((subject) => ucs.has(subject.name))) {
    return [];
  }
  if (dias.size > 0 && !dias.has(session.weekday)) {
    return [];
  }

  const base = buildBaseEvent(session, blockWeeks);

  if (session.classes.length === 0) {
    if (turmas.size > 0 || turnos.size > 0) return [];
    return [{ ...base, id: session.id }];
  }

  return session.classes
    .filter((classItem) => {
      const turno = String(classItem.shift);
      const matchesTurma = turmas.size === 0 || turmas.has(classItem.code);
      const matchesTurno = turnos.size === 0 || turnos.has(turno);
      return matchesTurma && matchesTurno;
    })
    .map((classItem) => ({
      ...base,
      id: `${session.id}-${classItem.code}`,
      turma: classItem.code,
    }));
}
