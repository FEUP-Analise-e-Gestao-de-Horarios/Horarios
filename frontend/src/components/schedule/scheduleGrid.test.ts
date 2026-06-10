import { describe, expect, it } from "vitest";
import type { WeekGridEvent } from "./WeekGrid";
import { formatWeekRanges, placeEventsOnGrid, toContiguousRuns } from "./scheduleGrid";

const ALL_DAYS = [0, 1, 2, 3, 4, 5];
// 08:00, half-hour slots, 19 slots covers up to 17:30.
const GRID_START_MIN = 8 * 60;
const SLOT_COUNT = 19;

function event(overrides: Partial<WeekGridEvent> & { id: string }): WeekGridEvent {
  return {
    weekday: "monday",
    startTime: 800,
    duration: 2,
    title: "ALG",
    type: "T",
    professor: "AL",
    sala: "B003",
    ...overrides,
  };
}

describe("toContiguousRuns", () => {
  it("collapses an empty list into no runs", () => {
    expect(toContiguousRuns([])).toEqual([]);
  });

  it("returns one run for a contiguous range", () => {
    expect(toContiguousRuns([0, 1, 2])).toEqual([{ start: 0, span: 3 }]);
  });

  it("splits gaps into separate runs", () => {
    expect(toContiguousRuns([0, 2])).toEqual([
      { start: 0, span: 1 },
      { start: 2, span: 1 },
    ]);
  });

  it("handles single elements", () => {
    expect(toContiguousRuns([3])).toEqual([{ start: 3, span: 1 }]);
  });
});

describe("formatWeekRanges", () => {
  it("returns an empty string for no weeks", () => {
    expect(formatWeekRanges([])).toBe("");
  });

  it("collapses a contiguous run into a single range", () => {
    expect(formatWeekRanges([1, 2, 3, 4, 5, 6, 7])).toBe("1-7");
  });

  it("splits gaps into comma-separated ranges", () => {
    expect(formatWeekRanges([1, 2, 3, 5, 6, 7])).toBe("1-3, 5-7");
  });

  it("renders a lone week without a dash", () => {
    expect(formatWeekRanges([3])).toBe("3");
  });

  it("sorts and de-duplicates before formatting", () => {
    expect(formatWeekRanges([3, 1, 2, 2])).toBe("1-3");
  });
});

describe("placeEventsOnGrid", () => {
  it("returns nothing for an empty event list", () => {
    expect(placeEventsOnGrid([], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT)).toEqual([]);
  });

  it("places a single event in the correct day and row", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weekday: "wednesday", startTime: 900 });
    const placed = placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
    expect(placed[0]).toMatchObject({
      dayCol: 2,
      rowStart: 2,
      span: 2,
      runs: [{ start: 0, span: 1 }],
    });
  });

  it("merges duplicate events from the same session into a single card", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A" }),
      event({ id: "s1-1B", turma: "1B" }),
    ];
    const placed = placeEventsOnGrid(events, ["1A", "1B"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
    expect(placed[0]?.runs).toEqual([{ start: 0, span: 2 }]);
  });

  it("splits a merged event into separate runs when turmas are non-adjacent", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A" }),
      event({ id: "s1-1C", turma: "1C" }),
    ];
    const placed = placeEventsOnGrid(
      events,
      ["1A", "1B", "1C"],
      ALL_DAYS,
      GRID_START_MIN,
      SLOT_COUNT,
    );
    expect(placed).toHaveLength(1);
    expect(placed[0]?.runs).toEqual([
      { start: 0, span: 1 },
      { start: 2, span: 1 },
    ]);
  });

  it("merges events that share the same class set into one card", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A", classCodes: ["1A", "1B"] }),
      event({ id: "s1-1B", turma: "1B", classCodes: ["1A", "1B"] }),
    ];
    const placed = placeEventsOnGrid(events, ["1A", "1B"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
    expect(placed[0]?.runs).toEqual([{ start: 0, span: 2 }]);
  });

  it("does not merge sessions that cover different class sets", () => {
    // Same day/time/type/title/teacher/room, but one session covers {1A,1B}
    // and the other {1A,1B,1C}; class membership keeps them as distinct blocks.
    const events: WeekGridEvent[] = [
      event({ id: "sX-1A", turma: "1A", classCodes: ["1A", "1B"] }),
      event({ id: "sX-1B", turma: "1B", classCodes: ["1A", "1B"] }),
      event({ id: "sY-1A", turma: "1A", classCodes: ["1A", "1B", "1C"] }),
      event({ id: "sY-1B", turma: "1B", classCodes: ["1A", "1B", "1C"] }),
      event({ id: "sY-1C", turma: "1C", classCodes: ["1A", "1B", "1C"] }),
    ];
    const placed = placeEventsOnGrid(
      events,
      ["1A", "1B", "1C"],
      ALL_DAYS,
      GRID_START_MIN,
      SLOT_COUNT,
    );
    expect(placed).toHaveLength(2);
  });

  it("treats class sets as unordered when keying", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A", classCodes: ["1A", "1B"] }),
      event({ id: "s1-1B", turma: "1B", classCodes: ["1B", "1A"] }),
    ];
    const placed = placeEventsOnGrid(events, ["1A", "1B"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
  });

  it("flags a session as partial when its weeks are a strict subset of the selection", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weeks: ["w1", "w2"] });
    const placed = placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT, [
      "w1",
      "w2",
      "w3",
    ]);
    expect(placed[0]?.isPartialWeeks).toBe(true);
  });

  it("does not flag a session that covers every selected week", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weeks: ["w1", "w2", "w3"] });
    const placed = placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT, [
      "w1",
      "w2",
      "w3",
    ]);
    expect(placed[0]?.isPartialWeeks).toBe(false);
  });

  it("unions weeks across a merged session before judging partialness", () => {
    // Same session split across two blocks (weeks w1-w2 and w3); together they
    // cover the whole selection, so the merged card is not partial.
    const events: WeekGridEvent[] = [
      event({ id: "s1-a", turma: "1A", classCodes: ["1A"], weeks: ["w1", "w2"] }),
      event({ id: "s1-b", turma: "1A", classCodes: ["1A"], weeks: ["w3"] }),
    ];
    const placed = placeEventsOnGrid(events, ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT, [
      "w1",
      "w2",
      "w3",
    ]);
    expect(placed).toHaveLength(1);
    expect(placed[0]?.isPartialWeeks).toBe(false);
  });

  it("never flags partial weeks when no weeks are selected", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weeks: ["w1"] });
    const placed = placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed[0]?.isPartialWeeks).toBe(false);
  });

  it("labels a partial session with its compact week range", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weeks: ["w1", "w2", "w3"] });
    const weekNumbers = new Map([
      ["w1", 1],
      ["w2", 2],
      ["w3", 3],
      ["w4", 4],
    ]);
    const placed = placeEventsOnGrid(
      [ev],
      ["1A"],
      ALL_DAYS,
      GRID_START_MIN,
      SLOT_COUNT,
      ["w1", "w2", "w3", "w4"],
      weekNumbers,
    );
    expect(placed[0]?.weekRangeLabel).toBe("1-3");
  });

  it("leaves the week-range label empty for a full-span session", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weeks: ["w1", "w2"] });
    const weekNumbers = new Map([
      ["w1", 1],
      ["w2", 2],
    ]);
    const placed = placeEventsOnGrid(
      [ev],
      ["1A"],
      ALL_DAYS,
      GRID_START_MIN,
      SLOT_COUNT,
      ["w1", "w2"],
      weekNumbers,
    );
    expect(placed[0]?.weekRangeLabel).toBe("");
  });

  it("does not merge events that differ on a merge-key field", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A", professor: "AL" }),
      event({ id: "s2-1B", turma: "1B", professor: "GT" }),
    ];
    const placed = placeEventsOnGrid(events, ["1A", "1B"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(2);
  });

  it("drops events whose turma is not in activeTurmas", () => {
    const events: WeekGridEvent[] = [
      event({ id: "s1-1A", turma: "1A" }),
      event({ id: "s1-2A", turma: "2A" }),
    ];
    const placed = placeEventsOnGrid(events, ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
    expect(placed[0]?.ev.id).toBe("s1-1A");
  });

  it("hides events on weekdays that aren't visible", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weekday: "friday" });
    const visible = [0, 1, 2, 3]; // monday..thursday
    expect(placeEventsOnGrid([ev], ["1A"], visible, GRID_START_MIN, SLOT_COUNT)).toEqual([]);
  });

  it("maps weekdays through visibleDayIndices, not WEEKDAYS", () => {
    const ev = event({ id: "s1-1A", turma: "1A", weekday: "wednesday" });
    const visible = [2, 3]; // wednesday is index 0 in the visible list
    const placed = placeEventsOnGrid([ev], ["1A"], visible, GRID_START_MIN, SLOT_COUNT);
    expect(placed[0]?.dayCol).toBe(0);
  });

  it("drops events that start before the grid", () => {
    const ev = event({ id: "early", turma: "1A", startTime: 700 });
    expect(placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT)).toEqual([]);
  });

  it("clips events that overrun the grid end", () => {
    const ev = event({ id: "late", turma: "1A", startTime: 1700, duration: 6 });
    const placed = placeEventsOnGrid([ev], ["1A"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed[0]?.span).toBe(SLOT_COUNT - placed[0]!.rowStart);
  });

  it("drops events when there are no turma columns to place them in", () => {
    const ev = event({ id: "no-turma", turma: undefined });
    expect(placeEventsOnGrid([ev], [], ALL_DAYS, GRID_START_MIN, SLOT_COUNT)).toEqual([]);
  });

  it("pins to the first turma column when an event has no turma but a filter is active", () => {
    const ev = event({ id: "no-turma", turma: undefined });
    const placed = placeEventsOnGrid([ev], ["1A", "1B"], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    expect(placed).toHaveLength(1);
    expect(placed[0]?.runs).toEqual([{ start: 0, span: 1 }]);
  });
});
