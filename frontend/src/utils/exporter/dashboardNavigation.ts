import type { WeekBlockResponse } from "@/types/project/sessions";
import { normalizeId } from "@/utils/exporter/ids";

export function parseConflictWeeks(searchParams: URLSearchParams): Set<string> {
  return new Set((searchParams.get("conflictWeeks") ?? "").split(",").filter(Boolean));
}

export function parseConflictSessionIds(searchParams: URLSearchParams): Set<string> {
  return new Set((searchParams.get("conflictSessions") ?? "").split(",").filter(Boolean));
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
