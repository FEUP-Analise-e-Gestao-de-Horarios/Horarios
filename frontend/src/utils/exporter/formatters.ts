import type {
  ExportFieldModification,
  ExportJsonValue,
  ExportModificationStep,
} from "@/types/exporter";
import type { Weekday } from "@/types/project/weekday";

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  monday: "Segunda",
  tuesday: "Terça",
  wednesday: "Quarta",
  thursday: "Quinta",
  friday: "Sexta",
  saturday: "Sábado",
};

const FIELD_LABELS: Record<string, string> = {
  start_time: "Hora",
  duration: "Duração",
  weekday: "Dia",
  week: "Semana",
  type: "Tipo",
  original_block_id: "Bloco original",
  rooms: "Salas",
  teachers: "Docentes",
  class_subjects: "Turmas",
  room_id: "ID da sala",
  room_name: "Sala",
  room_type: "Tipo de sala",
  room_size: "Dimensão",
  room_seats: "Lugares",
  teacher_id: "ID do docente",
  teacher_number: "Número",
  teacher_acronym: "Sigla",
  teacher_name: "Docente",
  class_id: "ID da turma",
  class_code: "Turma",
  class_shift: "Turno",
  subject_id: "ID da UC",
  subject_number: "Número da UC",
  subject_code: "Código da UC",
  subject_acronym: "Sigla",
  subject_name: "UC",
  acronym: "Sigla",
  name: "Nome",
  code: "Código",
};

const HIDDEN_DETAIL_KEYS = new Set([
  "id",
  "room_id",
  "teacher_id",
  "class_id",
  "subject_id",
  "original_block_id",
]);

export function formatTime(value: number): string {
  const hours = Math.floor(value / 100);
  const minutes = value % 100;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}h`;
}

export function formatDuration(slots: number): string {
  const minutes = slots * 30;
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h${String(rest).padStart(2, "0")}` : `${hours}h`;
}

export function formatJsonValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function cleanLegacyModelLabel(value: string): string {
  const subjectMatch = value.match(/^Subject\('([^']+)'\s+-\s+'([^']+)'\)$/);
  if (subjectMatch) return subjectMatch[2] ?? value;

  const teacherMatch = value.match(/^Teacher\('([^']+)'\s+-\s+'([^']+)'\)$/);
  if (teacherMatch) return teacherMatch[1] ?? value;

  const roomMatch = value.match(/^Room\('([^']+)'\)$/);
  if (roomMatch) return roomMatch[1] ?? value;

  const classMatch = value.match(/^Class\(code='([^']+)'/);
  if (classMatch) return classMatch[1] ?? value;

  return value;
}

export function formatFieldValue(field: string, value: unknown): string {
  if (field === "start_time" && typeof value === "number") return formatTime(value);
  if (field === "duration" && typeof value === "number") return formatDuration(value);
  if (field === "weekday" && typeof value === "string" && value in WEEKDAY_LABELS) {
    return WEEKDAY_LABELS[value as Weekday];
  }
  return formatJsonValue(value);
}

export function isColumnChange(
  change: ExportFieldModification,
): change is { old: unknown; new: unknown } {
  return typeof change === "object" && change !== null && "old" in change && "new" in change;
}

export function isRelationChange(change: ExportFieldModification): change is {
  added: unknown[];
  removed: unknown[];
} {
  return typeof change === "object" && change !== null && "added" in change && "removed" in change;
}

export function fieldLabel(name: string): string {
  return FIELD_LABELS[name] ?? name.replaceAll("_", " ");
}

export function preferredRecordLabel(record: Record<string, ExportJsonValue>): string {
  if (record.class_code && (record.subject_acronym || record.subject_name || record.subject_code)) {
    return `${formatJsonValue(record.class_code)} · ${formatJsonValue(
      record.subject_acronym ?? record.subject_name ?? record.subject_code,
    )}`;
  }

  const preferred =
    record.acronym ??
    record.subject_acronym ??
    record.teacher_acronym ??
    record.name ??
    record.teacher_name ??
    record.room_name ??
    record.room ??
    record.teacher ??
    record.subject ??
    record.class ??
    record.class_code ??
    record.code;

  return cleanLegacyModelLabel(formatJsonValue(preferred ?? record));
}

export function recordDetails(record: Record<string, ExportJsonValue>): string {
  return Object.entries(record)
    .filter(([key, value]) => !HIDDEN_DETAIL_KEYS.has(key) && value !== null && value !== undefined)
    .map(([key, value]) => `${fieldLabel(key)}: ${cleanLegacyModelLabel(formatJsonValue(value))}`)
    .join("\n");
}

export function tooltipAddsInformation(label: string, content?: string): boolean {
  if (!content) return false;
  if (
    content.includes("{") ||
    content.includes("}") ||
    content.includes("[") ||
    content.includes("]")
  ) {
    return false;
  }

  const visible = cleanLegacyModelLabel(label).trim();
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) return false;
  return lines.some((line) => {
    const [, ...rest] = line.split(": ");
    const value = cleanLegacyModelLabel(rest.join(": ") || line).trim();
    return value && value !== visible;
  });
}

export function formatWeekLabel(step: ExportModificationStep): string {
  const { weeks, week_range: weekRange } = step;
  if (
    weekRange.contiguous &&
    weekRange.start &&
    weekRange.end &&
    weekRange.start !== weekRange.end
  ) {
    return `${weekRange.start} a ${weekRange.end}`;
  }

  const uniqueWeeks = Array.from(new Set(weeks));
  return uniqueWeeks.join(", ") || step.session.week;
}

export function shouldShowWeekScope(step: ExportModificationStep): boolean {
  if (step.applies_to_all_weeks === false) return true;
  if (step.applies_to_all_weeks === true) return false;

  return new Set(step.weeks).size === 1;
}

export function relationChangeLabel(label: string, changeType: "added" | "removed"): string {
  const labels: Record<string, Record<"added" | "removed", string>> = {
    Turmas: { added: "Turmas adicionadas", removed: "Turmas removidas" },
    Salas: { added: "Salas adicionadas", removed: "Salas removidas" },
    Docentes: { added: "Docentes adicionados", removed: "Docentes removidos" },
  };

  return (
    labels[label]?.[changeType] ??
    `${label} ${changeType === "added" ? "adicionados" : "removidos"}`
  );
}

export function withConflictParams(
  path: string,
  row: { week: string; weeks?: string[]; session_ids: string[] },
): string {
  const weeks = row.weeks?.length ? row.weeks : [row.week];
  const firstWeek = [...new Set(weeks)].sort()[0] ?? row.week;
  const params = new URLSearchParams({
    week: firstWeek,
    conflictSessions: row.session_ids.join(","),
  });
  return `${path}?${params.toString()}`;
}
