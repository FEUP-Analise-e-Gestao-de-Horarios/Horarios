import type { ExportJsonValue, ExportSessionSnapshot } from "@/types/exporter";
import {
  cleanLegacyModelLabel,
  formatJsonValue,
  preferredRecordLabel,
  recordDetails,
  tooltipAddsInformation,
} from "@/utils/exporter/formatters";

export function relationRecord(item: unknown): { label: string; title?: string } {
  if (typeof item !== "object" || item === null) {
    const label = cleanLegacyModelLabel(formatJsonValue(item));
    return { label };
  }
  const record = item as Record<string, ExportJsonValue>;
  const label = preferredRecordLabel(record);
  const title = recordDetails(record);
  return { label, title: tooltipAddsInformation(label, title) ? title : undefined };
}

export function uniqueByLabel<T>(items: T[], getLabel: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const label = getLabel(item);
    if (seen.has(label)) return false;
    seen.add(label);
    return true;
  });
}

export function subjectTitleLabel(subject: ExportSessionSnapshot["subjects"][number]): string {
  return [subject.acronym ?? subject.name, subject.code].filter(Boolean).join(" ");
}
