import { describe, expect, it } from "vitest";
import type { Project } from "@/types/project/project";
import { isProjectProcessing, shouldRemindParallelSelection } from "./useParallelSessionsReminder";

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 1,
    name: "Projeto",
    url: "https://example.com",
    has_selected_parallel_sessions: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ingestion_started_at: "2026-01-01T00:00:00Z",
    ingestion_finished_at: "2026-01-01T00:05:00Z",
    ingestion_failed_at: null,
    ...overrides,
  };
}

describe("shouldRemindParallelSelection", () => {
  it("reminds when a finished project hasn't selected parallel sessions", () => {
    expect(shouldRemindParallelSelection(makeProject())).toBe(true);
  });

  it("stays quiet once the selection has been made", () => {
    expect(
      shouldRemindParallelSelection(makeProject({ has_selected_parallel_sessions: true })),
    ).toBe(false);
  });

  it("stays quiet while the project is still ingesting", () => {
    expect(shouldRemindParallelSelection(makeProject({ ingestion_finished_at: null }))).toBe(false);
  });

  it("stays quiet for a project whose ingestion failed", () => {
    expect(
      shouldRemindParallelSelection(
        makeProject({ ingestion_finished_at: null, ingestion_failed_at: "2026-01-01T00:05:00Z" }),
      ),
    ).toBe(false);
  });

  it("stays quiet when there is no project yet", () => {
    expect(shouldRemindParallelSelection(undefined)).toBe(false);
  });
});

describe("isProjectProcessing", () => {
  it("is processing while ingestion has started but not finished or failed", () => {
    expect(isProjectProcessing(makeProject({ ingestion_finished_at: null }))).toBe(true);
  });

  it("is not processing once ingestion has finished", () => {
    expect(isProjectProcessing(makeProject())).toBe(false);
  });

  it("is not processing before ingestion has started", () => {
    expect(
      isProjectProcessing(makeProject({ ingestion_started_at: null, ingestion_finished_at: null })),
    ).toBe(false);
  });

  it("is not processing once ingestion has failed", () => {
    expect(
      isProjectProcessing(
        makeProject({ ingestion_finished_at: null, ingestion_failed_at: "2026-01-01T00:05:00Z" }),
      ),
    ).toBe(false);
  });

  it("is not processing when there is no project yet", () => {
    expect(isProjectProcessing(undefined)).toBe(false);
  });
});
