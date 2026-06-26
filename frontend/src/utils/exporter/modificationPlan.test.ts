import { describe, expect, it } from "vitest";
import {
  buildDependencyLookup,
  buildModificationPlanItems,
} from "@/utils/exporter/modificationPlan";
import type { ExportModificationStep } from "@/types/exporter";

function makeStep(
  sessionId: string,
  options: Partial<Pick<ExportModificationStep, "type" | "dependencies">> = {},
): ExportModificationStep {
  return {
    type: options.type ?? "move",
    original_block_id: `block-${sessionId}`,
    session_ids: [sessionId],
    weeks: ["2026-01-05"],
    week_range: { start: "2026-01-05", end: "2026-01-05", contiguous: true },
    applies_to_all_weeks: true,
    modifications: {},
    dependencies: options.dependencies ?? [],
    session: {
      id: sessionId,
      start_time: 830,
      duration: 2,
      weekday: "monday",
      week: "2026-01-05",
      rooms: [],
      teachers: [],
      classes: [],
      subjects: [],
    },
  };
}

describe("buildModificationPlanItems", () => {
  it("groups connected exchange steps into a single cluster", () => {
    const first = makeStep("session-a", { type: "exchange", dependencies: ["session-b"] });
    const second = makeStep("session-b", { type: "exchange", dependencies: ["session-a"] });
    const items = buildModificationPlanItems([first, second]);

    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ kind: "exchangeCluster", steps: [first, second] });
  });

  it("leaves unconnected steps as single plan items", () => {
    const first = makeStep("session-a", { type: "exchange" });
    const second = makeStep("session-b");
    const items = buildModificationPlanItems([first, second]);

    expect(items).toEqual([
      { kind: "single", step: first },
      { kind: "single", step: second },
    ]);
  });
});

describe("buildDependencyLookup", () => {
  it("indexes session ids by visible plan order", () => {
    const items = buildModificationPlanItems([makeStep("019e-aaaa"), makeStep("019e-bbbb")]);
    const lookup = buildDependencyLookup(items);

    expect(lookup["019eaaaa"]).toMatchObject({
      anchor: "change-019eaaaa",
      label: "Passo 1",
      order: 0,
    });
    expect(lookup["019ebbbb"]).toMatchObject({
      anchor: "change-019ebbbb",
      label: "Passo 2",
      order: 1,
    });
  });
});
