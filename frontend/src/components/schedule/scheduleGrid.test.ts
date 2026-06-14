import { describe, expect, it } from "vitest";
import type { WeekGridEvent } from "./WeekGrid";
import {
  assignLaneSegments,
  buildArcPath,
  computeColumnWidths,
  computeRowHeights,
  computeRowOccupancy,
  formatWeekRanges,
  placeEventsOnGrid,
  toContiguousRuns,
  type PlacedEvent,
} from "./scheduleGrid";

const ALL_DAYS = [0, 1, 2, 3, 4, 5];
// 08:00, half-hour slots, 19 slots covers up to 17:30.
const GRID_START_MIN = 8 * 60;
const SLOT_COUNT = 19;

function event(overrides: Partial<WeekGridEvent> & { id: string }): WeekGridEvent {
  return {
    sessionId: overrides.id,
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

function placed(overrides: Partial<PlacedEvent>): PlacedEvent {
  return {
    ev: event({ id: "p" }),
    dayCol: 0,
    rowStart: 0,
    span: 1,
    runs: [{ start: 0, span: 1 }],
    isPartialWeeks: false,
    weekRangeLabel: "",
    ...overrides,
  };
}

describe("computeRowOccupancy", () => {
  it("marks the rows an event spans", () => {
    const occ = computeRowOccupancy([placed({ rowStart: 2, span: 3 })], [], 8);
    expect(occ).toEqual([false, false, true, true, true, false, false, false]);
  });

  it("marks mark-only rows too", () => {
    const occ = computeRowOccupancy([], [1, 4], 6);
    expect(occ).toEqual([false, true, false, false, true, false]);
  });

  it("clamps spans that run past the grid", () => {
    const occ = computeRowOccupancy([placed({ rowStart: 1, span: 10 })], [], 3);
    expect(occ).toEqual([false, true, true]);
  });
});

describe("computeRowHeights", () => {
  it("keeps occupied rows stretchable and collapses empty ones", () => {
    expect(computeRowHeights([true, false, true], "minmax(30px, 1fr)", 16)).toEqual([
      "minmax(30px, 1fr)",
      "16px",
      "minmax(30px, 1fr)",
    ]);
  });
});

describe("buildArcPath", () => {
  it("draws a shallow quadratic curve bowing up between two points", () => {
    // |dx|=300 -> lift = min(10, 15) = 10; peak = 50-10 = 40; mid x = 160.
    expect(buildArcPath(10, 50, 310, 50)).toBe("M 10 50 Q 160 40 310 50");
  });

  it("keeps a minimum bow so the arc clears the card tops", () => {
    // |dx|=30 -> lift = max(6, 1.5) = 6; peak = 50-6 = 44.
    expect(buildArcPath(10, 50, 40, 50)).toBe("M 10 50 Q 25 44 40 50");
  });

  it("clamps the peak so it never goes above the grid top", () => {
    expect(buildArcPath(0, 5, 10, 5)).toBe("M 0 5 Q 5 0 10 5");
  });

  it("keeps the peak at or below minPeakY so the header never hides it", () => {
    // lift 10; raw peak 100-10=90, but minPeakY 95 floors it.
    expect(buildArcPath(0, 100, 200, 100, 95)).toBe("M 0 100 Q 100 95 200 100");
  });
});

describe("assignLaneSegments", () => {
  it("keeps a non-overlapping event as one full-width segment", () => {
    const { laned, colLaneCount } = assignLaneSegments(
      [placed({ runs: [{ start: 0, span: 1 }] })],
      2,
      2,
    );
    expect(laned[0]?.segments).toEqual([{ start: 0, span: 1, lane: 0, laneCount: 1 }]);
    expect(colLaneCount).toEqual([1, 0]);
  });

  it("keeps a class shared across turmas as one wide segment when nothing overlaps", () => {
    const { laned } = assignLaneSegments([placed({ runs: [{ start: 0, span: 2 }] })], 2, 2);
    expect(laned[0]?.segments).toEqual([{ start: 0, span: 2, lane: 0, laneCount: 1 }]);
  });

  it("lanes two events that overlap in the same column", () => {
    const { laned, colLaneCount } = assignLaneSegments(
      [
        placed({ ev: event({ id: "a" }), rowStart: 0, span: 4, runs: [{ start: 0, span: 1 }] }),
        placed({ ev: event({ id: "b" }), rowStart: 2, span: 4, runs: [{ start: 0, span: 1 }] }),
      ],
      2,
      2,
    );
    expect(laned[0]?.segments).toEqual([{ start: 0, span: 1, lane: 0, laneCount: 2 }]);
    expect(laned[1]?.segments).toEqual([{ start: 0, span: 1, lane: 1, laneCount: 2 }]);
    expect(colLaneCount).toEqual([2, 0]);
  });

  it("splits a wide event only in the column where another event overlaps", () => {
    // A spans turmas 0-2; B overlaps only in turma 1 -> A becomes
    // [col0 full][col1 half][col2 full]; the breaks are where #20 draws arcs.
    const { laned, colLaneCount } = assignLaneSegments(
      [
        placed({ ev: event({ id: "a" }), rowStart: 0, span: 4, runs: [{ start: 0, span: 3 }] }),
        placed({ ev: event({ id: "b" }), rowStart: 0, span: 4, runs: [{ start: 1, span: 1 }] }),
      ],
      3,
      3,
    );
    expect(laned[0]?.segments).toEqual([
      { start: 0, span: 1, lane: 0, laneCount: 1 },
      { start: 1, span: 1, lane: 0, laneCount: 2 },
      { start: 2, span: 1, lane: 0, laneCount: 1 },
    ]);
    expect(laned[1]?.segments).toEqual([{ start: 1, span: 1, lane: 1, laneCount: 2 }]);
    expect(colLaneCount).toEqual([1, 2, 1]);
  });

  it("lets a non-overlapping event fill the column even when it is widened elsewhere", () => {
    // Column has a 2-event conflict later (B,C) plus a lone early event A.
    // A keeps laneCount 1 (full width) though the column widens to 2 for B,C.
    const { laned, colLaneCount } = assignLaneSegments(
      [
        placed({ ev: event({ id: "a" }), rowStart: 0, span: 2, runs: [{ start: 0, span: 1 }] }),
        placed({ ev: event({ id: "b" }), rowStart: 4, span: 4, runs: [{ start: 0, span: 1 }] }),
        placed({ ev: event({ id: "c" }), rowStart: 4, span: 4, runs: [{ start: 0, span: 1 }] }),
      ],
      1,
      1,
    );
    expect(laned[0]?.segments).toEqual([{ start: 0, span: 1, lane: 0, laneCount: 1 }]);
    expect(laned[1]?.segments).toEqual([{ start: 0, span: 1, lane: 0, laneCount: 2 }]);
    expect(laned[2]?.segments).toEqual([{ start: 0, span: 1, lane: 1, laneCount: 2 }]);
    expect(colLaneCount).toEqual([2]);
  });

  it("emits one card per laned column when two wide events share several columns", () => {
    // CF spans turmas 3-4; GEA spans turmas 0-4. They overlap in 3 and 4, which
    // must each become their own half-width card (not one card spanning both),
    // so CF and GEA sit side-by-side WITHIN each shared column.
    const { laned } = assignLaneSegments(
      [
        placed({ ev: event({ id: "cf" }), rowStart: 0, span: 6, runs: [{ start: 3, span: 2 }] }),
        placed({ ev: event({ id: "gea" }), rowStart: 2, span: 3, runs: [{ start: 0, span: 5 }] }),
      ],
      5,
      5,
    );
    expect(laned[0]?.segments).toEqual([
      { start: 3, span: 1, lane: 0, laneCount: 2 },
      { start: 4, span: 1, lane: 0, laneCount: 2 },
    ]);
    expect(laned[1]?.segments).toEqual([
      { start: 0, span: 3, lane: 0, laneCount: 1 },
      { start: 3, span: 1, lane: 1, laneCount: 2 },
      { start: 4, span: 1, lane: 1, laneCount: 2 },
    ]);
  });
});

describe("computeColumnWidths", () => {
  it("shrinks an empty turma column inside a busy day to the column minimum", () => {
    // 2 turmas, one day; col 0 has an event (1 lane), col 1 is empty.
    expect(computeColumnWidths([1, 0], 2, null, 64, 32, 40)).toEqual(["minmax(64px, 1fr)", "32px"]);
  });

  it("widens a column by its lane count so side-by-side events keep base width", () => {
    expect(computeColumnWidths([2, 0], 2, null, 64, 32, 40)).toEqual([
      "minmax(128px, 2fr)",
      "32px",
    ]);
  });

  it("uses the resized width times the lane count when columns are resized", () => {
    expect(computeColumnWidths([2, 1], 2, 80, 64, 32, 40)).toEqual(["160px", "80px"]);
  });

  it("collapses a fully empty day to its label width, split across columns", () => {
    // 2 turmas, one fully empty day; 40px label width / 2 columns = 20px each.
    expect(computeColumnWidths([0, 0], 2, null, 64, 32, 40)).toEqual(["20px", "20px"]);
  });
});
