import type { WeekGridEvent } from "@/components/dashboard/WeekGrid";
import type { WeekBlockResponse } from "@/types/project/sessions";
import type { Weekday } from "@/types/project/weekday";
import { normalizeId } from "@/utils/exporter/ids";

export type DashboardSessionHighlightTone = "conflict" | "added" | "removed";

export interface ExportSessionPreview extends WeekGridEvent {
  week: string;
}

export function parseConflictWeeks(searchParams: URLSearchParams): Set<string> {
  return new Set((searchParams.get("conflictWeeks") ?? "").split(",").filter(Boolean));
}

export function parseConflictSessionIds(searchParams: URLSearchParams): Set<string> {
  return new Set((searchParams.get("conflictSessions") ?? "").split(",").filter(Boolean));
}

export function parseHighlightedSessionIds(searchParams: URLSearchParams): Set<string> {
  const ids = parseConflictSessionIds(searchParams);
  const exportSession = searchParams.get("exportSession");
  if (exportSession) ids.add(exportSession);
  return ids;
}

export function parseSessionHighlightTone(
  searchParams: URLSearchParams,
): DashboardSessionHighlightTone {
  const change = searchParams.get("exportSessionChange");
  if (change === "added" || change === "removed") return change;
  return "conflict";
}

export interface ExportSessionContextIds {
  classIds: string[];
  roomIds: string[];
  teacherIds: string[];
}

function parseIdList(searchParams: URLSearchParams, key: string): string[] {
  return (searchParams.get(key) ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export function parseExportSessionContextIds(
  searchParams: URLSearchParams,
): ExportSessionContextIds {
  return {
    classIds: parseIdList(searchParams, "exportSessionClassIds"),
    roomIds: parseIdList(searchParams, "exportSessionRoomIds"),
    teacherIds: parseIdList(searchParams, "exportSessionTeacherIds"),
  };
}

export function hasHighlightedSession(
  sessionId: string,
  highlightedSessionIds: ReadonlySet<string>,
): boolean {
  const normalizedSessionId = normalizeId(sessionId);
  for (const candidate of highlightedSessionIds) {
    if (normalizeId(candidate) === normalizedSessionId) return true;
  }
  return false;
}

function normalizeWeekday(value: string | null): Weekday | null {
  const normalized = value?.toLowerCase();
  if (
    normalized === "monday" ||
    normalized === "tuesday" ||
    normalized === "wednesday" ||
    normalized === "thursday" ||
    normalized === "friday" ||
    normalized === "saturday"
  ) {
    return normalized;
  }
  return null;
}

export function parseExportSessionPreview(
  searchParams: URLSearchParams,
): ExportSessionPreview | null {
  const id = searchParams.get("exportSession");
  const week = searchParams.get("exportSessionWeek") ?? searchParams.get("week");
  const weekday = normalizeWeekday(searchParams.get("exportSessionWeekday"));
  const start = Number(searchParams.get("exportSessionStart"));
  const duration = Number(searchParams.get("exportSessionDuration"));

  if (!id || !week || !weekday || !Number.isFinite(start) || !Number.isFinite(duration)) {
    return null;
  }

  const bodyValue = searchParams.get("exportSessionBody");
  let body: string[] = [];
  if (bodyValue) {
    try {
      const parsed: unknown = JSON.parse(bodyValue);
      if (Array.isArray(parsed)) {
        body = parsed.filter((line): line is string => typeof line === "string");
      }
    } catch {
      body = [];
    }
  }

  return {
    id,
    week,
    weekday,
    startTime: start,
    duration,
    title: searchParams.get("exportSessionTitle") ?? "Aula",
    body,
    type: searchParams.get("exportSessionType") ?? undefined,
  };
}

export function withExportSessionPreview(
  events: WeekGridEvent[],
  activeBlock: WeekBlockResponse | null,
  preview: ExportSessionPreview | null,
): WeekGridEvent[] {
  if (!preview || !activeBlock?.weeks.includes(preview.week)) return events;
  const previewIds = new Set([preview.id]);
  if (events.some((event) => hasHighlightedSession(event.id, previewIds))) {
    return events.map((event) =>
      hasHighlightedSession(event.id, previewIds)
        ? {
            ...event,
            title: preview.title || event.title,
            body: preview.body?.length ? preview.body : event.body,
            type: preview.type ?? event.type,
          }
        : event,
    );
  }
  return [...events, preview];
}

export function withExportSessionWeekBlock(
  blocks: WeekBlockResponse[],
  preview: ExportSessionPreview | null,
): WeekBlockResponse[] {
  if (!preview) return blocks;
  if (blocks.some((block) => block.weeks.includes(preview.week))) return blocks;
  return [...blocks, { weeks: [preview.week], sessions: [] }];
}

export function weekBlockHasConflict(
  block: WeekBlockResponse,
  conflictWeeks: ReadonlySet<string>,
): boolean {
  if (!conflictWeeks.size) return false;
  return block.weeks.some((week) => conflictWeeks.has(week));
}

export function weekBlockButtonClass(active: boolean, hasConflict: boolean): string {
  if (active) return "bg-[#8c2d19] text-white border-[#8c2d19]";
  if (hasConflict) {
    return "bg-red-50 text-red-800 border-red-300 ring-2 ring-red-200 hover:bg-red-100";
  }
  return "bg-white text-[#08060d] border-[#e5e4e7] hover:bg-[#f9f7f4]";
}

export function findTargetWeekBlockIndex(
  blocks: WeekBlockResponse[],
  targetWeek: string | null,
): number {
  if (!targetWeek) return -1;
  return blocks.findIndex((block) => block.weeks.includes(targetWeek));
}
