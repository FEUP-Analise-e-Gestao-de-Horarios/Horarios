import { describe, expect, it } from "vitest";
import {
  findTargetWeekBlockIndex,
  hasHighlightedSession,
  parseConflictSessionIds,
  parseConflictWeeks,
  parseExportSessionContextIds,
  parseExportSessionPreview,
  parseHighlightedSessionIds,
  parseSessionHighlightTone,
  weekBlockButtonClass,
  weekBlockHasConflict,
  withExportSessionWeekBlock,
  withExportSessionPreview,
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

describe("parseHighlightedSessionIds", () => {
  it("includes added or removed exporter sessions", () => {
    const params = new URLSearchParams(
      "conflictSessions=session-1&exportSession=session-2&exportSessionChange=removed",
    );

    expect(parseHighlightedSessionIds(params)).toEqual(new Set(["session-1", "session-2"]));
  });
});

describe("parseSessionHighlightTone", () => {
  it("uses exporter added and removed colors when present", () => {
    expect(parseSessionHighlightTone(new URLSearchParams("exportSessionChange=added"))).toBe(
      "added",
    );
    expect(parseSessionHighlightTone(new URLSearchParams("exportSessionChange=removed"))).toBe(
      "removed",
    );
    expect(parseSessionHighlightTone(new URLSearchParams("conflictSessions=session-1"))).toBe(
      "conflict",
    );
  });
});

describe("parseExportSessionContextIds", () => {
  it("reads related dashboard resource ids for exporter session context", () => {
    const params = new URLSearchParams(
      "exportSessionClassIds=class-1,class-2&exportSessionRoomIds=room-1&exportSessionTeacherIds=teacher-1,teacher-2",
    );

    expect(parseExportSessionContextIds(params)).toEqual({
      classIds: ["class-1", "class-2"],
      roomIds: ["room-1"],
      teacherIds: ["teacher-1", "teacher-2"],
    });
  });
});

describe("parseExportSessionPreview", () => {
  it("reads the session preview carried from the exporter", () => {
    const params = new URLSearchParams(
      "exportSession=session-1&exportSessionWeek=2026-01-05&exportSessionWeekday=monday&exportSessionStart=830&exportSessionDuration=2&exportSessionTitle=IA&exportSessionBody=%5B%22ABC%22%5D&exportSessionType=TP",
    );

    expect(parseExportSessionPreview(params)).toMatchObject({
      id: "session-1",
      week: "2026-01-05",
      weekday: "monday",
      startTime: 830,
      duration: 2,
      title: "IA",
      body: ["ABC"],
      type: "TP",
    });
  });
});

describe("withExportSessionPreview", () => {
  it("adds a preview event only for the active week when the event is missing", () => {
    const preview = {
      id: "session-1",
      week: "2026-01-05",
      weekday: "monday" as const,
      startTime: 830,
      duration: 2,
      title: "IA",
    };

    expect(
      withExportSessionPreview([], { weeks: ["2026-01-05"], sessions: [] }, preview),
    ).toHaveLength(1);
    expect(
      withExportSessionPreview([], { weeks: ["2026-01-12"], sessions: [] }, preview),
    ).toHaveLength(0);
    expect(
      withExportSessionPreview(
        [{ id: "session-1", weekday: "monday", startTime: 830, duration: 2 }],
        { weeks: ["2026-01-05"], sessions: [] },
        preview,
      ),
    ).toHaveLength(1);
  });
});

describe("withExportSessionWeekBlock", () => {
  it("adds the exporter session week when the dashboard no longer has it", () => {
    const preview = {
      id: "session-1",
      week: "2026-01-05",
      weekday: "monday" as const,
      startTime: 830,
      duration: 2,
    };

    expect(withExportSessionWeekBlock([{ weeks: ["2026-01-12"], sessions: [] }], preview)).toEqual([
      { weeks: ["2026-01-12"], sessions: [] },
      { weeks: ["2026-01-05"], sessions: [] },
    ]);
    expect(withExportSessionWeekBlock([{ weeks: ["2026-01-05"], sessions: [] }], preview)).toEqual([
      { weeks: ["2026-01-05"], sessions: [] },
    ]);
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
