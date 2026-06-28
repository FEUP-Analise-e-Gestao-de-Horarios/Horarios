import { describe, expect, it } from "vitest";
import { compactExportToProjectExportPayload } from "@/utils/exporter/exportCompact";
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
          ["TEST (TEST001)"],
        ],
        [
          "class",
          "class1",
          "2026-01-05",
          ["2026-01-05"],
          "monday",
          830,
          2,
          2,
          ["session1", "session2"],
          ["TEST (TEST001)"],
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
      subject_labels: ["TEST (TEST001)"],
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
    expect(expanded.classes_conflicts[0]).toMatchObject({
      class_id: "class1",
      class_code: "1LEIC01",
      subject_labels: ["TEST (TEST001)"],
    });
  });

  it("resolves compact entity keys that differ only by UUID hyphens", () => {
    const hyphenatedSessionId = "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3";
    const normalizedSessionId = "019e21c08ed57722bd5e8ad5a3c750b3";
    const compact: CompactProjectExportPayload = {
      format: "compact_export_v1",
      entities: {
        rooms: {},
        teachers: {},
        classes: {
          "019e21c0-8ed5-7722-bd5e-8ad5a3c750c4": { class_code: "1LEIC01" },
        },
        subjects: {
          "019e21c0-8ed5-7722-bd5e-8ad5a3c750d5": {
            subject_acronym: "IA",
          },
        },
        sessions: {
          [hyphenatedSessionId]: {
            id: hyphenatedSessionId,
            start_time: 830,
            duration: 2,
            weekday: "monday",
            week: "2026-01-05",
            rooms: [],
            teachers: [],
            classes: ["1LEIC01"],
            subjects: [{ name: "Inteligencia Artificial", acronym: "IA", code: "IA001" }],
          },
        },
      },
      added_removed_sessions: { added: [], removed: [] },
      conflicts: [],
      modification_steps: [
        {
          type: "move",
          original_block_id: "block1",
          session_ids: [normalizedSessionId],
          weeks: ["2026-01-05"],
          week_range: { start: "2026-01-05", end: "2026-01-05", contiguous: true },
          applies_to_all_weeks: true,
          dependencies: [],
          modifications: {
            class_subjects: {
              added: [["019e21c08ed57722bd5e8ad5a3c750c4", "019e21c08ed57722bd5e8ad5a3c750d5"]],
              removed: [],
            },
          },
        },
      ],
    };

    const firstStep = compactExportToProjectExportPayload(compact).modification_steps[0];

    expect(firstStep?.session).toMatchObject({
      id: hyphenatedSessionId,
      start_time: 830,
      weekday: "monday",
      week: "2026-01-05",
      classes: ["1LEIC01"],
    });
    expect(firstStep?.modifications.class_subjects?.added[0]).toMatchObject({
      class_code: "1LEIC01",
      subject_acronym: "IA",
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
