import { describe, expect, it } from "vitest";
import {
  findTargetWeekBlockIndex,
  hasHighlightedSession,
  parseConflictSessionIds,
  parseConflictWeeks,
  weekBlockButtonClass,
  weekBlockHasConflict,
} from "@/utils/exporter/dashboardNavigation";

describe("parseConflictWeeks", () => {
  it("reads conflict weeks from the exporter navigation query", () => {
    const params = new URLSearchParams("conflictWeeks=2026-01-05%2C2026-01-12");

    expect(parseConflictWeeks(params)).toEqual(new Set(["2026-01-05", "2026-01-12"]));
  });
});

describe("parseConflictSessionIds", () => {
  it("reads highlighted session ids from the exporter navigation query", () => {
    const params = new URLSearchParams("conflictSessions=session-1%2Csession-2%2Csession-1");

    expect(parseConflictSessionIds(params)).toEqual(new Set(["session-1", "session-2"]));
  });
});

describe("hasHighlightedSession", () => {
  it("matches session ids even when hyphens differ", () => {
    expect(
      hasHighlightedSession(
        "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3",
        new Set(["019e21c08ed57722bd5e8ad5a3c750b3"]),
      ),
    ).toBe(true);
  });

  it("does not match unrelated session ids", () => {
    expect(hasHighlightedSession("session-1", new Set(["session-2"]))).toBe(false);
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

describe("findTargetWeekBlockIndex", () => {
  it("finds the block containing the target week", () => {
    expect(
      findTargetWeekBlockIndex(
        [
          { weeks: ["2026-01-05"], sessions: [] },
          { weeks: ["2026-01-12", "2026-01-19"], sessions: [] },
        ],
        "2026-01-19",
      ),
    ).toBe(1);
  });

  it("returns -1 for missing or empty target weeks", () => {
    expect(findTargetWeekBlockIndex([{ weeks: ["2026-01-05"], sessions: [] }], null)).toBe(-1);
    expect(findTargetWeekBlockIndex([{ weeks: ["2026-01-05"], sessions: [] }], "2026-02-02")).toBe(
      -1,
    );
  });
});

describe("weekBlockButtonClass", () => {
  it("keeps active styling before conflict highlight styling", () => {
    expect(weekBlockButtonClass(true, true)).toContain("bg-[#8c2d19]");
    expect(weekBlockButtonClass(false, true)).toContain("bg-red-50");
    expect(weekBlockButtonClass(false, false)).toContain("bg-white");
  });
});
