import type { ExportJsonValue, ExportSessionSnapshot } from "@/types/exporter";
import {
  cleanLegacyModelLabel,
  formatJsonValue,
  HIDDEN_DETAIL_KEYS,
  preferredRecordLabel,
  recordDetails,
  tooltipAddsInformation,
} from "@/utils/exporter/formatters";

function hasReadableRecordValue(record: Record<string, ExportJsonValue>): boolean {
  return Object.entries(record).some(
    ([key, value]) => !HIDDEN_DETAIL_KEYS.has(key) && value !== null && value !== undefined,
  );
}

function subjectChipLabel(subject: ExportSessionSnapshot["subjects"][number]): string {
  return subject.acronym ?? subject.name ?? subject.code;
}

export function relationFallbackLabel({
  fieldName,
  index,
  session,
}: {
  fieldName: string;
  index: number;
  session?: ExportSessionSnapshot;
}): string {
  if (fieldName === "class_subjects" && session) {
    const classLabel =
      session.classes[index] ?? (session.classes.length === 1 ? session.classes[0] : undefined);
    const subject =
      session.subjects[index] ?? (session.subjects.length === 1 ? session.subjects[0] : undefined);
    const subjectLabel = subject ? subjectChipLabel(subject) : undefined;
    const label = [classLabel, subjectLabel].filter(Boolean).join(" · ");

    if (label) return label;
  }

  return `${fieldName} ${index + 1}`;
}

export function relationRecord(
  item: unknown,
  fallbackLabel?: string,
): { label: string; title?: string } {
  if (typeof item !== "object" || item === null) {
    const label = cleanLegacyModelLabel(formatJsonValue(item));
    return { label };
  }
  const record = item as Record<string, ExportJsonValue>;
  if (fallbackLabel && !hasReadableRecordValue(record)) {
    return { label: fallbackLabel };
  }

  const label = preferredRecordLabel(record);
  if (fallbackLabel && (label.includes("{") || label.includes("}"))) {
    return { label: fallbackLabel };
  }

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
