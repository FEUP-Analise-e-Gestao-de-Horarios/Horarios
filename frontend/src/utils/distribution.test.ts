import { describe, expect, it } from "vitest";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { computeDistribution } from "./distribution";

function ev(partial: Partial<WeekGridEvent>): WeekGridEvent {
  return {
    id: Math.random().toString(),
    sessionId: "s",
    weekday: "monday",
    startTime: 800,
    duration: 2,
    ...partial,
  };
}

describe("computeDistribution", () => {
  it("splits each weekday into type sub-columns with distinct-session counts", () => {
    const { weekdays, typesByDay, rows } = computeDistribution([
      ev({ title: "AED", uc: "Algoritmos", type: "TP", weekday: "monday", sessionId: "a" }),
      ev({ title: "AED", uc: "Algoritmos", type: "P", weekday: "monday", sessionId: "b" }),
      ev({ title: "AED", uc: "Algoritmos", type: "P", weekday: "monday", sessionId: "c" }),
      ev({ title: "AED", uc: "Algoritmos", type: "P", weekday: "monday", sessionId: "d" }),
    ]);

    expect(weekdays).toEqual(["monday"]);
    // Canonical type order puts TP before P.
    expect(typesByDay.monday).toEqual(["TP", "P"]);
    expect(rows[0]!.perDay.monday).toEqual({ TP: 1, P: 3 });
    expect(rows[0]!.perDay.tuesday).toEqual({});
  });

  it("unions the day's types across UCs so columns align", () => {
    const { typesByDay } = computeDistribution([
      ev({ title: "AED", uc: "Algoritmos", type: "T", weekday: "monday", sessionId: "a" }),
      ev({ title: "BD", uc: "Bases", type: "TP", weekday: "monday", sessionId: "b" }),
    ]);
    expect(typesByDay.monday).toEqual(["T", "TP"]);
  });

  it("counts each session once even when expanded across turmas", () => {
    const { rows } = computeDistribution([
      ev({ title: "PR", uc: "Prog", type: "T", weekday: "tuesday", sessionId: "x", turma: "01" }),
      ev({ title: "PR", uc: "Prog", type: "T", weekday: "tuesday", sessionId: "x", turma: "02" }),
    ]);
    expect(rows[0]!.perDay.tuesday).toEqual({ T: 1 });
  });

  it("sorts rows by acronym and returns no weekdays for no events", () => {
    expect(computeDistribution([]).weekdays).toEqual([]);
    const { rows } = computeDistribution([
      ev({ title: "ZZ", uc: "Zeta", type: "T", sessionId: "1" }),
      ev({ title: "AA", uc: "Alfa", type: "TP", sessionId: "2" }),
    ]);
    expect(rows.map((r) => r.acronym)).toEqual(["AA", "ZZ"]);
  });

  it("keeps a co-taught session its own row, independent of event order", () => {
    const coTaught = ev({
      title: "ALG, BD",
      uc: "Algoritmos",
      subjectNames: ["Algoritmos", "Bases de Dados"],
      type: "TP",
      sessionId: "joint",
    });
    const standalone = ev({ title: "BD", uc: "Bases de Dados", type: "T", sessionId: "solo" });

    const a = computeDistribution([coTaught, standalone]);
    const b = computeDistribution([standalone, coTaught]);
    // Rows keyed by the acronym they display, so order can't rename or merge them.
    expect(a.rows.map((r) => r.acronym)).toEqual(["ALG, BD", "BD"]);
    expect(b.rows.map((r) => r.acronym)).toEqual(a.rows.map((r) => r.acronym));
    // The full name (tooltip) comes from the deduped subject names.
    expect(a.rows.find((r) => r.acronym === "ALG, BD")?.name).toBe("Algoritmos, Bases de Dados");
  });
});
