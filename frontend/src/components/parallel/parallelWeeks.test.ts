import { describe, expect, it } from "vitest";
import { formatWeek, weekGrid, weekSpanLabel } from "./parallelWeeks";

describe("formatWeek", () => {
  it("formats an ISO date as DD/MM", () => {
    expect(formatWeek("2025-09-15")).toBe("15/09");
  });

  it("returns malformed input unchanged", () => {
    expect(formatWeek("2025-09")).toBe("2025-09");
  });
});

describe("weekSpanLabel", () => {
  it("joins distinct weeks with a dash", () => {
    expect(weekSpanLabel("2025-09-15", "2025-12-20")).toBe("15/09–20/12");
  });

  it("collapses a single-week span", () => {
    expect(weekSpanLabel("2025-09-15", "2025-09-15")).toBe("15/09");
  });
});

describe("weekGrid", () => {
  it("returns empty for no nodes", () => {
    expect(weekGrid([])).toEqual([]);
  });

  it("steps weekly across the widest span of all nodes", () => {
    const grid = weekGrid([
      { first_week: "2025-09-22", last_week: "2025-09-29" },
      { first_week: "2025-09-15", last_week: "2025-10-06" },
    ]);
    expect(grid).toEqual(["2025-09-15", "2025-09-22", "2025-09-29", "2025-10-06"]);
  });

  it("keeps a single-week candidate as one entry", () => {
    expect(weekGrid([{ first_week: "2025-09-15", last_week: "2025-09-15" }])).toEqual([
      "2025-09-15",
    ]);
  });

  it("crosses month and year boundaries", () => {
    const grid = weekGrid([{ first_week: "2025-12-22", last_week: "2026-01-05" }]);
    expect(grid).toEqual(["2025-12-22", "2025-12-29", "2026-01-05"]);
  });

  it("returns empty for malformed dates", () => {
    expect(weekGrid([{ first_week: "not-a-date", last_week: "2025-09-15" }])).toEqual([]);
  });

  it("caps runaway spans", () => {
    const grid = weekGrid([{ first_week: "2000-01-03", last_week: "2030-01-07" }]);
    expect(grid.length).toBe(60);
  });
});
