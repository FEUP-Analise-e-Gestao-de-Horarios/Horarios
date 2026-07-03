import { describe, expect, it } from "vitest";
import {
  buildConflictSessionIds,
  buildConflictLookup,
  conflictAulasCount,
  conflictCardAnchorId,
  teacherConflictName,
} from "@/utils/exporter/conflicts";
import { withConflictParams } from "@/utils/exporter/formatters";
import type { ProjectExportPayload } from "@/types/exporter";

const payload: ProjectExportPayload = {
  added_removed_sessions: { added: [], removed: [] },
  rooms_conflicts: [
    {
      room_id: "room-1",
      room_name: "A1",
      week: "2026-01-12",
      weeks: ["2026-01-12", "2026-01-05"],
      weekday: "monday",
      start_time: 830,
      duration: 2,
      collisions: 2,
      session_ids: ["019e-aaaa"],
    },
  ],
  teacher_conflicts: [
    {
      teacher_id: "teacher-1",
      teacher_number: 7,
      teacher_acronym: "ABC",
      teacher_name: "Alice Example",
      week: "2026-01-05",
      weekday: "tuesday",
      start_time: 1000,
      duration: 2,
      collisions: 2,
      session_ids: ["019e-bbbb", "019ebbbb"],
    },
  ],
  classes_conflicts: [
    {
      class_id: "class-1",
      class_code: "1LEIC01",
      week: "2026-01-05",
      weekday: "wednesday",
      start_time: 1130,
      duration: 2,
      collisions: 2,
      session_ids: ["019e-cccc", "019e-dddd"],
    },
  ],
  modification_steps: [],
};

describe("buildConflictLookup", () => {
  it("maps normalized session ids to the first matching conflict target", () => {
    const lookup = buildConflictLookup(payload);

    expect(lookup["019eaaaa"]).toEqual({
      anchor: "export-conflict-room-2026-01-12-monday-830-0",
      label: "Sala A1",
    });
    expect(lookup["019ebbbb"]).toEqual({
      anchor: "export-conflict-teacher-2026-01-05-tuesday-1000-0",
      label: "Docente ABC",
    });
  });
});

describe("buildConflictSessionIds", () => {
  it("collects normalized unique session ids from all conflict lists", () => {
    expect(Array.from(buildConflictSessionIds(payload)).sort()).toEqual([
      "019eaaaa",
      "019ebbbb",
      "019ecccc",
      "019edddd",
    ]);
  });
});

describe("conflict anchors and URLs", () => {
  it("keeps conflict anchors and query params stable", () => {
    const conflict = payload.rooms_conflicts[0];

    expect(conflict).toBeDefined();
    if (!conflict) return;

    expect(conflictCardAnchorId("room", conflict, 0)).toBe(
      "export-conflict-room-2026-01-12-monday-830-0",
    );
    expect(withConflictParams("/rooms/room-1", conflict)).toBe(
      "/rooms/room-1?week=2026-01-05&conflictSessions=019e-aaaa&conflictWeeks=2026-01-12%2C2026-01-05",
    );
  });
});

describe("conflictAulasCount", () => {
  it("derives aulas count from unique sessions divided by weeks", () => {
    expect(conflictAulasCount(payload.teacher_conflicts[0]!)).toBe(1);
    expect(
      conflictAulasCount({
        ...payload.rooms_conflicts[0]!,
        weeks: ["2026-01-05", "2026-01-12"],
        session_ids: ["session-1", "session-2", "session-3", "session-4"],
      }),
    ).toBe(2);
  });
});

describe("teacherConflictName", () => {
  it("shows only the acronym when the teacher acronym and name are equal", () => {
    expect(
      teacherConflictName({
        teacher_id: "teacher-1",
        teacher_number: 7,
        teacher_acronym: "ABC",
        teacher_name: "ABC",
        week: "2026-01-05",
        weekday: "monday",
        start_time: 830,
        duration: 2,
        collisions: 2,
        session_ids: [],
      }),
    ).toBe("ABC");
  });

  it("shows acronym and name when they differ", () => {
    expect(
      teacherConflictName({
        teacher_id: "teacher-1",
        teacher_number: 7,
        teacher_acronym: "ABC",
        teacher_name: "Alice Example",
        week: "2026-01-05",
        weekday: "monday",
        start_time: 830,
        duration: 2,
        collisions: 2,
        session_ids: [],
      }),
    ).toBe("ABC · Alice Example");
  });
});
