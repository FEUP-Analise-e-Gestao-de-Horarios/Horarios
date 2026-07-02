import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import type { SessionResponse } from "@/types/project/sessions";

/** Course group buckets, in display order. */
export const COURSE_GROUPS = ["Licenciaturas", "Mestrados", "Pós-Graduações", "Outros"] as const;

export type CourseGroupLabel = (typeof COURSE_GROUPS)[number];

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
    blockId: session.original_block_id,
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
    teacherIds: session.teachers.map((teacher) => teacher.id),
    roomIds: session.rooms.map((room) => room.id),
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
