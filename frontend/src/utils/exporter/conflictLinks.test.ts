import { describe, expect, it } from "vitest";
import {
  buildClassConflictHref,
  buildRoomConflictHref,
  buildTeacherConflictHref,
} from "@/utils/exporter/conflictLinks";

describe("conflict route builders", () => {
  it("builds the room detail route with conflict query params", () => {
    expect(
      buildRoomConflictHref("project-1", {
        room_id: "room-1",
        room_name: "A1",
        week: "2026-01-12",
        weeks: ["2026-01-12", "2026-01-05"],
        weekday: "monday",
        start_time: 830,
        duration: 2,
        collisions: 2,
        session_ids: ["019e-aaaa", "019e-bbbb"],
      }),
    ).toBe(
      "/projects/project-1/dashboard/rooms/room-1?week=2026-01-05&conflictSessions=019e-aaaa%2C019e-bbbb&conflictWeeks=2026-01-12%2C2026-01-05",
    );
  });

  it("builds the teacher and class detail routes with the correct path shape", () => {
    expect(
      buildTeacherConflictHref("project-1", {
        teacher_id: "teacher-1",
        teacher_number: 7,
        teacher_acronym: "ABC",
        teacher_name: "Alice Example",
        week: "2026-01-05",
        weekday: "tuesday",
        start_time: 1000,
        duration: 2,
        collisions: 2,
        session_ids: ["session-1"],
      }),
    ).toContain("/projects/project-1/dashboard/teachers/teacher-1?");

    expect(
      buildClassConflictHref("project-1", {
        class_id: "class-1",
        class_code: "1LEIC01",
        week: "2026-01-05",
        weekday: "wednesday",
        start_time: 1130,
        duration: 2,
        collisions: 2,
        session_ids: ["session-1"],
      }),
    ).toContain("/projects/project-1/dashboard/classes/class-1?");
  });
});
