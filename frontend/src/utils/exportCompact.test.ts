import { describe, expect, it } from "vitest";
import { compactExportToProjectExportPayload } from "@/utils/exportCompact";
import type { CompactProjectExportPayload, ProjectExportPayload } from "@/types/exporter";

describe("compactExportToProjectExportPayload", () => {
  it("expands compact conflicts and modification relations into the legacy export shape", () => {
    const compact: CompactProjectExportPayload = {
      format: "compact_export_v1",
      entities: {
        rooms: {
          room1: { room_name: "A1" },
        },
        teachers: {
          teacher1: {
            teacher_number: 7,
            teacher_acronym: "ABC",
            teacher_name: "Alice Example",
          },
        },
        classes: {
          class1: { class_code: "1LEIC01", class_shift: 1 },
        },
        subjects: {
          subject1: {
            subject_number: 42,
            subject_code: "TEST001",
            subject_acronym: "TEST",
            subject_name: "Testing",
          },
        },
        sessions: {
          session1: {
            id: "session1",
            start_time: 830,
            duration: 2,
            weekday: "monday",
            week: "2026-01-05",
            rooms: ["A1"],
            teachers: [{ number: 7, acronym: "ABC", name: "Alice Example" }],
            classes: ["1LEIC01"],
            subjects: [{ name: "Testing", acronym: "TEST", code: "TEST001" }],
          },
        },
      },
      added_removed_sessions: { added: [], removed: [] },
      conflicts: [
        [
          "room",
          "room1",
          "2026-01-05",
          ["2026-01-05"],
          "monday",
          830,
          2,
          2,
          ["session1", "session2"],
        ],
      ],
      modification_steps: [
        {
          type: "move",
          original_block_id: "block1",
          session_ids: ["session1"],
          weeks: ["2026-01-05"],
          week_range: { start: "2026-01-05", end: "2026-01-05", contiguous: true },
          applies_to_all_weeks: true,
          dependencies: [],
          modifications: {
            rooms: { added: ["room1"], removed: [] },
            class_subjects: {
              added: [["class1", "subject1"]],
              removed: [],
            },
          },
        },
      ],
    };

    const expanded = compactExportToProjectExportPayload(compact);
    const firstConflict = expanded.rooms_conflicts[0];
    const firstStep = expanded.modification_steps[0];

    expect(firstConflict).toBeDefined();
    expect(firstStep).toBeDefined();

    expect(firstConflict).toMatchObject({
      room_id: "room1",
      room_name: "A1",
      session_ids: ["session1", "session2"],
    });
    expect(firstStep?.session.id).toBe("session1");
    expect(firstStep?.modifications.rooms?.added[0]).toEqual({
      room_id: "room1",
      room_name: "A1",
    });
    expect(firstStep?.modifications.class_subjects?.added[0]).toEqual({
      class_id: "class1",
      class_code: "1LEIC01",
      class_shift: 1,
      subject_id: "subject1",
      subject_number: 42,
      subject_code: "TEST001",
      subject_acronym: "TEST",
      subject_name: "Testing",
    });
  });

  it("leaves already-expanded payloads untouched", () => {
    const expanded: ProjectExportPayload = {
      added_removed_sessions: { added: [], removed: [] },
      rooms_conflicts: [],
      teacher_conflicts: [],
      classes_conflicts: [],
      modification_steps: [],
    };

    expect(compactExportToProjectExportPayload(expanded)).toBe(expanded);
  });
});
