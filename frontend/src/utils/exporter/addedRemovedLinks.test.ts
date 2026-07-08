import { describe, expect, it } from "vitest";
import { buildAddedRemovedSessionHref } from "@/utils/exporter/addedRemovedLinks";
import type { ExportSessionRecord } from "@/types/exporter";

const session: ExportSessionRecord = {
  id: "session-1",
  week: "2026-01-05",
  weekday: "monday",
  start_time: 830,
  duration: 2,
  type: "TP",
  class_ids: ["class-1"],
  room_ids: ["room-1"],
  teacher_ids: ["teacher-1"],
  classes: ["1LEIC01"],
  rooms: ["A1"],
  teachers: [{ number: 7, acronym: "ABC", name: "Alice Example" }],
  subjects: [{ name: "Inteligencia Artificial", acronym: "IA", code: "IA001" }],
};

describe("buildAddedRemovedSessionHref", () => {
  it("targets the combined dashboard context and carries the added session preview", () => {
    const href = buildAddedRemovedSessionHref("project-1", session, "added");

    expect(href).toContain("/projects/project-1/dashboard/export-session?");
    expect(href).toContain("week=2026-01-05");
    expect(href).toContain("exportSession=session-1");
    expect(href).toContain("exportSessionChange=added");
    expect(href).toContain("exportSessionClassIds=class-1");
    expect(href).toContain("exportSessionRoomIds=room-1");
    expect(href).toContain("exportSessionTeacherIds=teacher-1");
    expect(href).toContain("exportSessionTitle=1LEIC01+%C2%B7+IA+%28IA001%29");
  });

  it("accepts weekday values from older cached payloads", () => {
    const href = buildAddedRemovedSessionHref(
      "project-1",
      { ...session, weekday: "MONDAY" as typeof session.weekday },
      "removed",
    );

    expect(href).toContain("exportSessionWeekday=monday");
    expect(href).toContain("exportSessionChange=removed");
  });

  it("returns null when the session has no dashboard target", () => {
    expect(buildAddedRemovedSessionHref("project-1", { id: "session-1" }, "removed")).toBeNull();
  });
});
