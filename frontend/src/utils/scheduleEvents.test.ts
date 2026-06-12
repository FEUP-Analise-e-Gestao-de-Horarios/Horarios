import { describe, expect, it } from "vitest";
import {
  getCourseGroupLabel,
  sessionToEvents,
  sortValuesByReference,
  type ScheduleFilters,
} from "./scheduleEvents";
import type { ClassBase } from "@/types/project/class";
import type { RoomBase } from "@/types/project/room";
import type { SessionResponse } from "@/types/project/sessions";
import type { SubjectBase } from "@/types/project/subject";
import type { TeacherBase } from "@/types/project/teacher";

describe("sortValuesByReference", () => {
  it("orders values to match the reference", () => {
    expect(sortValuesByReference(["c", "a", "b"], ["a", "b", "c"])).toEqual(["a", "b", "c"]);
  });

  it("drops values that aren't in the reference", () => {
    expect(sortValuesByReference(["a", "x", "b"], ["a", "b", "c"])).toEqual(["a", "b"]);
  });

  it("de-duplicates", () => {
    expect(sortValuesByReference(["b", "a", "a", "b"], ["a", "b"])).toEqual(["a", "b"]);
  });

  it("returns empty when nothing matches", () => {
    expect(sortValuesByReference(["x", "y"], ["a", "b"])).toEqual([]);
  });
});

describe("getCourseGroupLabel", () => {
  it("matches Licenciaturas", () => {
    expect(getCourseGroupLabel("Licenciatura em Informática")).toBe("Licenciaturas");
  });

  it("matches Mestrados", () => {
    expect(getCourseGroupLabel("Mestrado em Engenharia")).toBe("Mestrados");
  });

  it("matches Pós-Graduações via accented and unaccented variants", () => {
    expect(getCourseGroupLabel("Pós-Graduação em X")).toBe("Pós-Graduações");
    expect(getCourseGroupLabel("Pos-graduacao em X")).toBe("Pós-Graduações");
    expect(getCourseGroupLabel("Especialização Pós Graduada")).toBe("Pós-Graduações");
  });

  it("falls back to Outros", () => {
    expect(getCourseGroupLabel("Curso de Verão")).toBe("Outros");
    expect(getCourseGroupLabel("")).toBe("Outros");
  });
});

const NO_FILTERS: ScheduleFilters = {
  ucs: new Set(),
  turnos: new Set(),
  turmas: new Set(),
  dias: new Set(),
};

function makeTeacher(overrides: Partial<TeacherBase> = {}): TeacherBase {
  return { id: "t1", number: 1, acronym: "AL", name: "Ada Lovelace", ...overrides };
}

function makeSubject(overrides: Partial<SubjectBase> = {}): SubjectBase {
  return {
    id: "u1",
    year_id: "y1",
    number: 1,
    code: "ALG01",
    acronym: "ALG",
    name: "Algoritmos",
    ...overrides,
  };
}

function makeClass(overrides: Partial<ClassBase> = {}): ClassBase {
  return { id: "c1", year_id: "y1", code: "1A", shift: 1, ...overrides };
}

function makeRoom(overrides: Partial<RoomBase> = {}): RoomBase {
  return { id: "r1", name: "B003", type: "Aula", size: null, seats: null, ...overrides };
}

function makeSession(overrides: Partial<SessionResponse> = {}): SessionResponse {
  return {
    id: "s1",
    original_block_id: "b1",
    week: "2024-03-04",
    weekday: "monday",
    start_time: 800,
    duration: 4,
    type: "T",
    teachers: [makeTeacher()],
    subjects: [makeSubject()],
    classes: [
      makeClass({ id: "c1", code: "1A", shift: 1 }),
      makeClass({ id: "c2", code: "2A", shift: 2 }),
    ],
    rooms: [makeRoom()],
    ...overrides,
  };
}

describe("sessionToEvents", () => {
  it("emits one event per class when no filter is set", () => {
    const events = sessionToEvents(makeSession(), NO_FILTERS);
    expect(events.map((e) => e.turma)).toEqual(["1A", "2A"]);
    expect(events.map((e) => e.id)).toEqual(["s1-1A", "s1-2A"]);
  });

  it("returns one event with the session id when there are no classes", () => {
    const events = sessionToEvents(makeSession({ classes: [] }), NO_FILTERS);
    expect(events).toHaveLength(1);
    expect(events[0]?.id).toBe("s1");
    expect(events[0]?.turma).toBeUndefined();
  });

  it("hides class-less sessions when a turma or turno filter is active", () => {
    const session = makeSession({ classes: [] });
    expect(sessionToEvents(session, { ...NO_FILTERS, turmas: new Set(["1A"]) })).toEqual([]);
    expect(sessionToEvents(session, { ...NO_FILTERS, turnos: new Set(["1"]) })).toEqual([]);
  });

  it("filters classes by turma", () => {
    const events = sessionToEvents(makeSession(), { ...NO_FILTERS, turmas: new Set(["2A"]) });
    expect(events.map((e) => e.turma)).toEqual(["2A"]);
  });

  it("filters classes by turno", () => {
    const events = sessionToEvents(makeSession(), { ...NO_FILTERS, turnos: new Set(["1"]) });
    expect(events.map((e) => e.turma)).toEqual(["1A"]);
  });

  it("hides the session when its weekday isn't selected", () => {
    expect(sessionToEvents(makeSession(), { ...NO_FILTERS, dias: new Set(["tuesday"]) })).toEqual(
      [],
    );
  });

  it("hides the session when none of its subjects match the uc filter", () => {
    expect(sessionToEvents(makeSession(), { ...NO_FILTERS, ucs: new Set(["Outra UC"]) })).toEqual(
      [],
    );
  });

  it("keeps the session when at least one subject matches the uc filter", () => {
    const events = sessionToEvents(makeSession(), { ...NO_FILTERS, ucs: new Set(["Algoritmos"]) });
    expect(events).toHaveLength(2);
  });

  it("derives the title from subject acronyms", () => {
    const events = sessionToEvents(
      makeSession({
        subjects: [
          makeSubject({ id: "u1", code: "ALG01", acronym: "ALG", name: "Algoritmos" }),
          makeSubject({ id: "u2", code: "BD01", acronym: "BD", name: "Bases de Dados" }),
        ],
      }),
      NO_FILTERS,
    );
    expect(events[0]?.title).toBe("ALG, BD");
  });

  it("falls back to the session type when there are no subjects", () => {
    const events = sessionToEvents(makeSession({ subjects: [] }), NO_FILTERS);
    expect(events[0]?.title).toBe("T");
  });

  it("populates body lines from teacher and room acronyms when present", () => {
    const events = sessionToEvents(makeSession(), NO_FILTERS);
    expect(events[0]?.body).toEqual(["AL", "B003"]);
  });

  it("stamps the session id and structured teachers/rooms on every event", () => {
    const events = sessionToEvents(makeSession(), NO_FILTERS);
    for (const ev of events) {
      expect(ev.sessionId).toBe("s1");
      expect(ev.teachers).toEqual([{ id: "t1", acronym: "AL", name: "Ada Lovelace" }]);
      expect(ev.rooms).toEqual([{ id: "r1", name: "B003" }]);
    }
  });
});
