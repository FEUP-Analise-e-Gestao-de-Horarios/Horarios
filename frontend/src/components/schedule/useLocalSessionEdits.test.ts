import { describe, expect, it } from "vitest";
import type { SessionResponse, WeekBlockResponse } from "@/types/project/sessions";
import {
  applySessionOverrides,
  buildSessionOverride,
  type OverrideLookups,
} from "./useLocalSessionEdits";
import type { EventDrawerFormState } from "./useEventDrawerForm";

function session(partial: Partial<SessionResponse> & { id: string }): SessionResponse {
  return {
    original_block_id: "b",
    week: "2026-01-01",
    weekday: "monday",
    start_time: 800,
    duration: 2,
    type: "TP",
    teachers: [],
    subjects: [],
    classes: [],
    rooms: [],
    ...partial,
  };
}

function block(sessions: SessionResponse[]): WeekBlockResponse {
  return { weeks: ["2026-01-01"], sessions };
}

describe("applySessionOverrides", () => {
  it("returns the input untouched when there are no overrides", () => {
    const blocks = [block([session({ id: "s1" })])];
    expect(applySessionOverrides(blocks, {})).toBe(blocks);
  });

  it("passes undefined through", () => {
    expect(
      applySessionOverrides(undefined, {
        s1: { weekday: "tuesday", start_time: 900, duration: 4 },
      }),
    ).toBeUndefined();
  });

  it("patches only the matching session's slot", () => {
    const blocks = [block([session({ id: "s1" }), session({ id: "s2", weekday: "friday" })])];
    const result = applySessionOverrides(blocks, {
      s1: { weekday: "wednesday", start_time: 1030, duration: 4 },
    });
    const sessions = result?.[0]?.sessions ?? [];
    expect(sessions[0]).toMatchObject({
      id: "s1",
      weekday: "wednesday",
      start_time: 1030,
      duration: 4,
    });
    expect(sessions[1]).toMatchObject({
      id: "s2",
      weekday: "friday",
      start_time: 800,
      duration: 2,
    });
  });

  it("keeps blocks without a matching session referentially stable", () => {
    const matched = block([session({ id: "s1" })]);
    const untouched = block([session({ id: "s2" })]);
    const result = applySessionOverrides([matched, untouched], {
      s1: { weekday: "tuesday", start_time: 900, duration: 2 },
    });
    expect(result![1]).toBe(untouched);
    expect(result![0]).not.toBe(matched);
  });
});

function form(partial: Partial<EventDrawerFormState>): EventDrawerFormState {
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [],
    selectedSalaOverride: [],
    selectedTurmasOverride: [],
    selectedWeekday: "monday",
    startTime: "08:00",
    durationSlots: 2,
    ...partial,
  };
}

const lookups: OverrideLookups = {
  teachersById: new Map([["t1", { id: "t1", number: 1, acronym: "AB", name: "Ana" }]]),
  roomsById: new Map([["r1", { id: "r1", name: "B001", type: "Anf", size: null, seats: "40" }]]),
  subjectsByName: new Map([
    ["Algoritmos", { id: "sub1", number: 1, code: "AED", acronym: "AED", name: "Algoritmos" }],
  ]),
  classesByCode: new Map([["1LEIC01", { id: "c1", year_id: "y", code: "1LEIC01", shift: 1 }]]),
};

describe("buildSessionOverride", () => {
  it("resolves the form into a session patch (slot + content)", () => {
    const result = buildSessionOverride(
      form({
        selectedWeekday: "wednesday",
        startTime: "10:30",
        durationSlots: 4,
        selectedUcOverride: "Algoritmos",
        selectedDocenteOverride: ["t1"],
        selectedSalaOverride: ["r1"],
        selectedTurmasOverride: ["1LEIC01"],
      }),
      lookups,
    );
    expect(result).toMatchObject({ weekday: "wednesday", start_time: 1030, duration: 4 });
    expect(result.teachers).toEqual([{ id: "t1", number: 1, acronym: "AB", name: "Ana" }]);
    expect(result.rooms?.[0]?.id).toBe("r1");
    expect(result.classes?.[0]?.code).toBe("1LEIC01");
    expect(result.subjects?.[0]?.name).toBe("Algoritmos");
  });

  it("drops ids missing from the lookups and leaves an unknown UC untouched", () => {
    const result = buildSessionOverride(
      form({ selectedDocenteOverride: ["t1", "ghost"], selectedUcOverride: "Desconhecida" }),
      lookups,
    );
    expect(result.teachers).toHaveLength(1);
    expect(result.subjects).toBeUndefined();
  });
});
