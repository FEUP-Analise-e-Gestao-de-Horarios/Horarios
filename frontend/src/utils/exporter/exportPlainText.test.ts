import { describe, expect, it } from "vitest";
import { buildPlainTextExport } from "@/utils/exporter/exportPlainText";
import type { ProjectExportPayload } from "@/types/exporter";

function makeStep(sessionId: string, dependencies: string[] = []) {
  return {
    type: "exchange" as const,
    original_block_id: `block-${sessionId}`,
    session_ids: [sessionId],
    weeks: ["2026-01-05"],
    week_range: { start: "2026-01-05", end: "2026-01-05", contiguous: true },
    applies_to_all_weeks: true,
    modifications: {
      rooms: {
        added: [{ room_id: "room-2", room_name: "B2" }],
        removed: [{ room_id: "room-1", room_name: "A1" }],
      },
    },
    dependencies,
    session: {
      id: sessionId,
      start_time: 830,
      duration: 2,
      weekday: "monday" as const,
      week: "2026-01-05",
      rooms: ["A1"],
      teachers: [{ number: 7, acronym: "ABC", name: "Alice Example" }],
      classes: ["1LEIC01"],
      subjects: [{ name: "Testing", acronym: "TEST", code: "TEST001" }],
    },
  };
}

describe("buildPlainTextExport", () => {
  it("exports added/removed classes and the modification plan without summary or conflicts sections", () => {
    const data: ProjectExportPayload = {
      added_removed_sessions: {
        added: [{ id: "added-1" }],
        removed: [],
      },
      rooms_conflicts: [
        {
          room_id: "room-1",
          room_name: "A1",
          week: "2026-01-05",
          weeks: ["2026-01-05"],
          weekday: "monday",
          start_time: 830,
          duration: 2,
          collisions: 2,
          session_ids: ["session-a", "session-b"],
          subject_labels: ["TEST (TEST001)"],
        },
      ],
      teacher_conflicts: [],
      classes_conflicts: [],
      modification_steps: [
        {
          ...makeStep("session-c", ["session-a"]),
          type: "move",
        },
        makeStep("session-a", ["session-b"]),
        makeStep("session-b", ["session-a"]),
      ],
    };

    const text = buildPlainTextExport(data);

    expect(text).not.toContain("Resumo");
    expect(text).not.toContain("Conflitos (1)");
    expect(text).not.toContain("Salas · 1");
    expect(text).not.toContain("- A1 · TEST (TEST001) | 2 aulas | 2026-01-05 | Segunda | 08:30h");
    expect(text).toContain("Aulas Adicionadas e removidas");
    expect(text).toContain("Plano de Modificações (2)");
    expect(text).toContain("Passo 1 · Mover");
    expect(text).toContain("Passo 2 · Troca");
    expect(text).toContain("2 alterações agrupadas");
    expect(text).toContain("Esta alteração causa um conflito por resolver: Sala A1");
    expect(text).toContain("Causa um conflito resolvido pelo Passo 2");
  });
});
