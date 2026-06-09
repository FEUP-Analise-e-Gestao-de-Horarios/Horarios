import type {
  ExportFieldModification,
  ExportJsonValue,
  ExportModificationStep,
  ProjectExportPayload,
} from "@/types/exporter";
import type { Weekday } from "@/types/project/weekday";

const WEEKDAY_LABELS: Record<Weekday, string> = {
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

function formatTime(value: number): string {
  const hours = Math.floor(value / 100);
  const minutes = value % 100;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}h`;
}

function formatDuration(slots: number): string {
  const minutes = slots * 30;
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h${String(rest).padStart(2, "0")}` : `${hours}h`;
}

function formatJsonValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function cleanLegacyModelLabel(value: string): string {
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

function fieldLabel(name: string): string {
  return FIELD_LABELS[name] ?? name.replaceAll("_", " ");
}

function formatFieldValue(field: string, value: unknown): string {
  if (field === "start_time" && typeof value === "number") return formatTime(value);
  if (field === "duration" && typeof value === "number") return formatDuration(value);
  if (field === "weekday" && typeof value === "string" && value in WEEKDAY_LABELS) {
    return WEEKDAY_LABELS[value as Weekday];
  }
  return formatJsonValue(value);
}

function isColumnChange(change: ExportFieldModification): change is { old: unknown; new: unknown } {
  return typeof change === "object" && change !== null && "old" in change && "new" in change;
}

function isRelationChange(change: ExportFieldModification): change is {
  added: unknown[];
  removed: unknown[];
} {
  return typeof change === "object" && change !== null && "added" in change && "removed" in change;
}

function preferredRecordLabel(record: Record<string, ExportJsonValue>): string {
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

function recordDetails(record: Record<string, ExportJsonValue>): string {
  return Object.entries(record)
    .filter(([key, value]) => !HIDDEN_DETAIL_KEYS.has(key) && value !== null && value !== undefined)
    .map(([key, value]) => `${fieldLabel(key)}: ${cleanLegacyModelLabel(formatJsonValue(value))}`)
    .join("\n");
}

function relationRecord(item: unknown): { label: string } {
  if (typeof item !== "object" || item === null) {
    return { label: cleanLegacyModelLabel(formatJsonValue(item)) };
  }
  return { label: preferredRecordLabel(item as Record<string, ExportJsonValue>) };
}

function relationChangeLabel(label: string, changeType: "added" | "removed"): string {
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

function sessionTitle(session: ExportModificationStep["session"]): string {
  const subjects = Array.from(
    new Set(session.subjects.map((subject) => subject.acronym ?? subject.name)),
  ).join(", ");
  const classes = Array.from(new Set(session.classes)).join(", ");
  return [subjects, classes].filter(Boolean).join(" · ") || "Sessão";
}

function changeTitle(session: ExportModificationStep["session"]): string {
  return `${sessionTitle(session)} · ${WEEKDAY_LABELS[session.weekday]} ${formatTime(
    session.start_time,
  )}`;
}

function formatWeekLabel(step: ExportModificationStep): string {
  const { weeks, week_range: weekRange } = step;
  if (
    weekRange.contiguous &&
    weekRange.start &&
    weekRange.end &&
    weekRange.start !== weekRange.end
  ) {
    return `${weekRange.start} a ${weekRange.end}`;
  }

  return Array.from(new Set(weeks)).join(", ") || step.session.week;
}

function normalizeId(value: string): string {
  return value.replaceAll("-", "");
}

function textLinesForRecord(record: unknown, fallbackLabel: string): string[] {
  if (typeof record !== "object" || record === null) return [`- ${fallbackLabel}`];

  const values = record as Record<string, ExportJsonValue>;
  const details = recordDetails(values)
    .split("\n")
    .filter((line) => line.length > 0);
  const preferredTitle = preferredRecordLabel(values);
  const title =
    details.length === 0 || preferredTitle.includes("{") ? fallbackLabel : preferredTitle;

  if (!details.length) return [`- ${title}`];
  return [`- ${title}`, ...details.map((line) => `  ${line}`)];
}

function textRelationLabel(item: unknown, fallbackLabel: string): string {
  if (typeof item !== "object" || item === null) return fallbackLabel;

  const record = item as Record<string, ExportJsonValue>;
  const hasReadableValue = Object.entries(record).some(
    ([key, value]) => !HIDDEN_DETAIL_KEYS.has(key) && value !== null && value !== undefined,
  );

  if (!hasReadableValue) return fallbackLabel;

  const label = relationRecord(item).label;
  return label.includes("{") ? fallbackLabel : label;
}

function formatTextChange(
  name: string,
  change: ExportFieldModification,
  stepType: ExportModificationStep["type"],
): string[] {
  if (isColumnChange(change)) {
    return [
      `- ${fieldLabel(name)}: ${formatFieldValue(name, change.old)} -> ${formatFieldValue(
        name,
        change.new,
      )}`,
    ];
  }

  if (!isRelationChange(change)) return [];

  const label = fieldLabel(name);
  const clusterRelations = stepType === "exchange" && label === "Turmas";
  const lines: string[] = [];

  if (change.added.length > 0) {
    lines.push(
      `- ${clusterRelations ? "Adicionado" : relationChangeLabel(label, "added")}: ${change.added
        .map((item, index) => textRelationLabel(item, `${label} ${index + 1}`))
        .join(", ")}`,
    );
  }

  if (change.removed.length > 0) {
    lines.push(
      `- ${clusterRelations ? "Removido" : relationChangeLabel(label, "removed")}: ${change.removed
        .map((item, index) => textRelationLabel(item, `${label} ${index + 1}`))
        .join(", ")}`,
    );
  }

  return lines;
}

function buildStepNumberBySessionId(steps: ExportModificationStep[]): Map<string, number> {
  const stepNumberBySessionId = new Map<string, number>();

  steps.forEach((step, index) => {
    for (const sessionId of step.session_ids) {
      stepNumberBySessionId.set(normalizeId(sessionId), index + 1);
    }
  });

  return stepNumberBySessionId;
}

function buildPlainTextExport(data: ProjectExportPayload): string {
  const stepNumberBySessionId = buildStepNumberBySessionId(data.modification_steps);
  const lines = [
    "Exportacao de alteracoes de horario",
    `Gerado em: ${new Date().toLocaleString("pt-PT")}`,
    "",
    "Resumo",
    `- Aulas adicionadas: ${data.added_removed_sessions.added.length}`,
    `- Aulas removidas: ${data.added_removed_sessions.removed.length}`,
    `- Passos de modificacao: ${data.modification_steps.length}`,
    "",
    `Aulas adicionadas (${data.added_removed_sessions.added.length})`,
  ];

  if (data.added_removed_sessions.added.length) {
    lines.push(
      ...data.added_removed_sessions.added.flatMap((record, index) =>
        textLinesForRecord(record, `Aula adicionada ${index + 1}`),
      ),
    );
  } else {
    lines.push("- Sem aulas adicionadas.");
  }

  lines.push("", `Aulas removidas (${data.added_removed_sessions.removed.length})`);

  if (data.added_removed_sessions.removed.length) {
    lines.push(
      ...data.added_removed_sessions.removed.flatMap((record, index) =>
        textLinesForRecord(record, `Aula removida ${index + 1}`),
      ),
    );
  } else {
    lines.push("- Sem aulas removidas.");
  }

  lines.push("", `Plano de modificacoes (${data.modification_steps.length})`);

  if (!data.modification_steps.length) lines.push("- Sem modificacoes.");

  data.modification_steps.forEach((step, index) => {
    const changeLines = Object.entries(step.modifications).flatMap(([name, change]) =>
      change && !HIDDEN_DETAIL_KEYS.has(name) ? formatTextChange(name, change, step.type) : [],
    );
    const dependencySteps = Array.from(
      new Set(
        step.dependencies.flatMap((dependency) => {
          const stepNumber = stepNumberBySessionId.get(normalizeId(String(dependency)));
          return stepNumber && stepNumber > index + 1 ? [stepNumber] : [];
        }),
      ),
    );

    lines.push(
      "",
      `${index + 1}. ${step.type === "exchange" ? "Troca" : "Mover"} - ${changeTitle(
        step.session,
      )}`,
      `   Semanas: ${formatWeekLabel(step)}`,
    );

    if (dependencySteps.length) {
      lines.push(
        `   Dependencias: ${dependencySteps
          .toSorted((left, right) => left - right)
          .map((stepNumber) => `Passo ${stepNumber}`)
          .join(", ")}`,
      );
    }

    if (changeLines.length) {
      lines.push("   Alteracoes:", ...changeLines.map((line) => `   ${line}`));
    } else {
      lines.push("   Alteracoes: sem detalhes.");
    }
  });

  return `${lines.join("\n")}\n`;
}

export function downloadPlainTextExport(data: ProjectExportPayload) {
  const blob = new Blob([buildPlainTextExport(data)], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `alteracoes-horario-${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
