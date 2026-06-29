import { describe, expect, it } from "vitest";
import {
  parseConflictWeeks,
  weekBlockButtonClass,
  weekBlockHasConflict,
} from "@/utils/exporter/conflictNavigation";

describe("parseConflictWeeks", () => {
  it("reads conflict weeks from the exporter navigation query", () => {
    const params = new URLSearchParams("conflictWeeks=2026-01-05%2C2026-01-12");

    expect(parseConflictWeeks(params)).toEqual(new Set(["2026-01-05", "2026-01-12"]));
  });
});

describe("weekBlockHasConflict", () => {
  it("matches blocks containing any conflict week", () => {
    const conflictWeeks = new Set(["2026-01-12"]);

    expect(weekBlockHasConflict({ weeks: ["2026-01-05"], sessions: [] }, conflictWeeks)).toBe(
      false,
    );
    expect(
      weekBlockHasConflict({ weeks: ["2026-01-05", "2026-01-12"], sessions: [] }, conflictWeeks),
    ).toBe(true);
  });
});

describe("weekBlockButtonClass", () => {
  it("keeps active styling before conflict highlight styling", () => {
    expect(weekBlockButtonClass(true, true)).toContain("bg-[#8c2d19]");
    expect(weekBlockButtonClass(false, true)).toContain("bg-red-50");
    expect(weekBlockButtonClass(false, false)).toContain("bg-white");
  });
});
