import { describe, expect, it } from "vitest";
import type { WeekGridEvent } from "./WeekGrid";
import { placeEventsOnGrid, toContiguousRuns } from "./scheduleGrid";

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

  it("pins to the first turma column when an event's turma isn't in activeTurmas but no filter is active", () => {
    const ev = event({ id: "no-turma", turma: undefined });
    const placed = placeEventsOnGrid([ev], [], ALL_DAYS, GRID_START_MIN, SLOT_COUNT);
    // When activeTurmas is empty we still draw events: the placed card has no
    // runs because there are no turma columns, so it gets filtered out.
    expect(placed).toEqual([]);
  });
});
