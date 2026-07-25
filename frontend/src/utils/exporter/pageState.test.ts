import { describe, expect, it } from "vitest";
import {
  exporterConflictsOpenStorageKey,
  exporterScrollStorageKey,
  exporterSelectedConflictStorageKey,
  parseStoredScrollTop,
  shouldRestoreExporterScroll,
} from "@/utils/exporter/pageState";

describe("exporter storage keys", () => {
  it("namespaces keys by project id", () => {
    expect(exporterScrollStorageKey("project-1")).toBe("exporter-scroll-top:project-1");
    expect(exporterSelectedConflictStorageKey("project-1")).toBe(
      "exporter-selected-conflict:project-1",
    );
    expect(exporterConflictsOpenStorageKey("project-1")).toBe("exporter-conflicts-open:project-1");
  });
});

describe("parseStoredScrollTop", () => {
  it("parses valid numeric values and rejects invalid ones", () => {
    expect(parseStoredScrollTop("420")).toBe(420);
    expect(parseStoredScrollTop(null)).toBeNull();
    expect(parseStoredScrollTop("abc")).toBeNull();
  });
});

describe("shouldRestoreExporterScroll", () => {
  it("restores only when a project has saved scroll and no selected conflict is pending", () => {
    expect(
      shouldRestoreExporterScroll({
        projectId: "project-1",
        restoredProjectId: null,
        hasSelectedConflict: false,
        savedScrollTop: 420,
      }),
    ).toBe(true);
  });

  it("suppresses scroll restore for empty ids, repeated restores, or selected conflicts", () => {
    expect(
      shouldRestoreExporterScroll({
        projectId: "",
        restoredProjectId: null,
        hasSelectedConflict: false,
        savedScrollTop: 420,
      }),
    ).toBe(false);
    expect(
      shouldRestoreExporterScroll({
        projectId: "project-1",
        restoredProjectId: "project-1",
        hasSelectedConflict: false,
        savedScrollTop: 420,
      }),
    ).toBe(false);
    expect(
      shouldRestoreExporterScroll({
        projectId: "project-1",
        restoredProjectId: null,
        hasSelectedConflict: true,
        savedScrollTop: 420,
      }),
    ).toBe(false);
    expect(
      shouldRestoreExporterScroll({
        projectId: "project-1",
        restoredProjectId: null,
        hasSelectedConflict: false,
        savedScrollTop: null,
      }),
    ).toBe(false);
  });
});
