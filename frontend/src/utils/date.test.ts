import { describe, expect, it } from "vitest";
import { formatBlockLabel, formatDateLabel, formatShortDate, formatWeekRange } from "./date";
import type { WeekBlockResponse } from "@/types/project/sessions";

describe("formatDateLabel", () => {
  it("flips ISO-style dates to DD-MM-YYYY", () => {
    expect(formatDateLabel("2024-03-05")).toBe("05-03-2024");
  });

  it("returns the input unchanged when it doesn't have three hyphen-separated parts", () => {
    expect(formatDateLabel("2024")).toBe("2024");
    expect(formatDateLabel("2024-03")).toBe("2024-03");
    expect(formatDateLabel("")).toBe("");
  });
});

describe("formatWeekRange", () => {
  it("returns empty for an empty list", () => {
    expect(formatWeekRange([])).toBe("");
  });

  it("collapses a single-week block to one date", () => {
    expect(formatWeekRange(["2024-03-05"])).toBe("05-03-2024");
  });

  it("collapses a block whose first and last dates match", () => {
    expect(formatWeekRange(["2024-03-05", "2024-03-05"])).toBe("05-03-2024");
  });

  it("formats a multi-week block as first - last", () => {
    expect(formatWeekRange(["2024-03-05", "2024-03-12", "2024-03-19"])).toBe(
      "05-03-2024 - 19-03-2024",
    );
  });
});

describe("formatShortDate", () => {
  it("renders day and month for a valid ISO date", () => {
    // Both `05 mar.` and `05/03` are valid outputs depending on whether the
    // host has full ICU data, so the assertion only insists on the day part
    // and a non-empty rest.
    const result = formatShortDate("2024-03-05");
    expect(result).toContain("05");
    expect(result.length).toBeGreaterThan(2);
  });

  it("throws when the input doesn't have three hyphen-separated parts", () => {
    expect(() => formatShortDate("2024-03")).toThrow();
    expect(() => formatShortDate("")).toThrow();
  });
});

describe("formatBlockLabel", () => {
  function makeBlock(weeks: string[]): WeekBlockResponse {
    return { weeks, sessions: [] };
  }

  it("returns the em-dash placeholder for an empty block", () => {
    expect(formatBlockLabel(makeBlock([]))).toBe("—");
  });

  it("singularises 'semana' for a single-week block", () => {
    const label = formatBlockLabel(makeBlock(["2024-03-05"]));
    expect(label.endsWith("· 1 semana")).toBe(true);
  });

  it("pluralises and joins the range with an en-dash for multi-week blocks", () => {
    const label = formatBlockLabel(makeBlock(["2024-03-05", "2024-03-12", "2024-03-19"]));
    expect(label).toContain(" – ");
    expect(label.endsWith("· 3 semanas")).toBe(true);
  });
});
