import type { ExportModificationStep, ExportSessionRecord } from "@/types/exporter";
import { normalizeId } from "@/utils/exporter/ids";

export type ExportChecklistSessionChange = "added" | "removed";

export function addedRemovedChecklistKey(
  change: ExportChecklistSessionChange,
  session: ExportSessionRecord,
): string {
  return `${change}:${normalizeId(session.id)}`;
}

export function modificationChecklistKey(step: ExportModificationStep): string {
  const sessionKey = step.session_ids
    .map((sessionId) => normalizeId(sessionId))
    .sort()
    .join(",");
  return `modification:${sessionKey || normalizeId(step.original_block_id)}`;
}
