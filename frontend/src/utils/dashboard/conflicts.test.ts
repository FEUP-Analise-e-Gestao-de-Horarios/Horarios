import { describe, expect, it } from "vitest";
import type { SessionResponse } from "@/types/project/sessions";
import { findConflictingSessionIds, findConflictWeeks } from "./conflicts";

function session(
  id: string,
  start_time: number,
  duration = 2,
  weekday: SessionResponse["weekday"] = "monday",
): SessionResponse {
  return {
    id,
    start_time,
    duration,
    weekday,
    week: "2026-01-05",
    original_block_id: id,
    type: "T",
    teachers: [],
    subjects: [],
    classes: [],
    rooms: [],
  };
}

describe("findConflictingSessionIds", () => {
  it("marks both overlapping sessions", () => {
    const result = findConflictingSessionIds([session("a", 900), session("b", 930)]);

    expect(result).toEqual(new Set(["a", "b"]));
  });

  it("does not mark adjacent sessions or sessions on different days", () => {
    const result = findConflictingSessionIds([
      session("a", 900),
      session("b", 1000),
      session("c", 930, 2, "tuesday"),
    ]);

    expect(result).toEqual(new Set());
  });

  it("marks sessions that overlap a red block", () => {
    const result = findConflictingSessionIds(
      [session("a", 900)],
      [{ id: "red", weekday: "monday", hour: 930 }],
    );

    expect(result).toEqual(new Set(["a"]));
  });
});

describe("findConflictWeeks", () => {
  it("returns every week represented by a conflicting block", () => {
    const result = findConflictWeeks([
      { weeks: ["2026-01-05", "2026-01-12"], sessions: [session("a", 900), session("b", 930)] },
      { weeks: ["2026-01-19"], sessions: [session("c", 900)] },
    ]);

    expect(result).toEqual(new Set(["2026-01-05", "2026-01-12"]));
  });
});
