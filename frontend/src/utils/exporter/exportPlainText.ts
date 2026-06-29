import type {
  ExportFieldModification,
  ExportJsonValue,
  ExportModificationStep,
  ExportSessionSnapshot,
  ProjectExportPayload,
} from "@/types/exporter";
import { buildConflictLookup, buildConflictSessionIds } from "@/utils/exporter/conflicts";
import {
  cleanLegacyModelLabel,
  fieldLabel,
  formatDuration,
  formatFieldValue,
  formatJsonValue,
  formatTime,
  formatWeekLabel,
  HIDDEN_DETAIL_KEYS,
  isColumnChange,
  isRelationChange,
  preferredRecordLabel,
  recordDetails,
  relationChangeLabel,
  shouldShowWeekScope,
  WEEKDAY_LABELS,
} from "@/utils/exporter/formatters";
import { normalizeId } from "@/utils/exporter/ids";
import {
  buildDependencyLookup,
  buildModificationPlanItems,
  type DependencyLookup,
  type ModificationPlanItem,
} from "@/utils/exporter/modificationPlan";
import { relationRecord, subjectTitleLabel, uniqueByLabel } from "@/utils/exporter/relations";

function sessionTitle(session: ExportSessionSnapshot): string {
  const subjects = uniqueByLabel(session.subjects, subjectTitleLabel)
    .map((subject) =>
      [subject.acronym ?? subject.name, subject.code ? `(${subject.code})` : ""]
        .filter(Boolean)
        .join(" "),
    )
    .join(", ");
  const classes = uniqueByLabel(session.classes, (classCode) => classCode).join(", ");
  return [classes, subjects].filter(Boolean).join(" · ") || "Sessão";
}

function changeTitle(session: ExportSessionSnapshot): string {
  return `${sessionTitle(session)} · ${WEEKDAY_LABELS[session.weekday]} ${formatTime(
    session.start_time,
  )}`;
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
  if (typeof item !== "object" || item === null) {
    return cleanLegacyModelLabel(formatJsonValue(item));
  }

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

function visibleDependencies(
  step: ExportModificationStep,
  dependencyLookup: DependencyLookup,
  currentOrder: number,
): string[] {
  return Array.from(
    new Set(
      step.dependencies.flatMap((dependency) => {
        const target = dependencyLookup[normalizeId(String(dependency))];
        return target && target.order > currentOrder ? [target.label] : [];
      }),
    ),
  );
}

function stepDetailsLines({
  step,
  dependencies,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
  currentOrder,
}: {
  step: ExportModificationStep;
  dependencies: string[];
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ReturnType<typeof buildConflictLookup>;
  currentOrder: number;
}): string[] {
  const hasUnsolvedConflict = step.session_ids.some((sessionId) =>
    conflictSessionIds.has(normalizeId(sessionId)),
  );
  const conflictTarget = step.session_ids
    .map((sessionId) => conflictLookup[normalizeId(sessionId)])
    .find((target) => target !== undefined);
  const dependencyLabels = visibleDependencies(
    { ...step, dependencies },
    dependencyLookup,
    currentOrder,
  ).toSorted();
  const changeLines = Object.entries(step.modifications).flatMap(([name, change]) =>
    change && !HIDDEN_DETAIL_KEYS.has(name) ? formatTextChange(name, change, step.type) : [],
  );
  const lines = [`   ${changeTitle(step.session)}`];

  if (shouldShowWeekScope(step)) {
    lines.push(`   Apenas semanas ${formatWeekLabel(step)}`);
  }

  lines.push(
    `   Duração: ${formatDuration(step.session.duration)}`,
    `   Semana: ${formatWeekLabel(step)}`,
  );

  if (hasUnsolvedConflict) {
    lines.push(
      `   Esta alteração causa um conflito por resolver${
        conflictTarget ? `: ${conflictTarget.label}` : ""
      }`,
    );
  }

  if (dependencyLabels.length) {
    lines.push(`   Causa um conflito resolvido pelo ${dependencyLabels.join(", ")}`);
  }

  if (changeLines.length) {
    lines.push("   Alterações:", ...changeLines.map((line) => `   ${line}`));
  } else {
    lines.push("   Alterações: sem detalhes.");
  }

  return lines;
}

function modificationItemLines({
  item,
  index,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
}: {
  item: ModificationPlanItem;
  index: number;
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ReturnType<typeof buildConflictLookup>;
}): string[] {
  if (item.kind === "single") {
    return [
      "",
      `Passo ${index + 1} · ${item.step.type === "exchange" ? "Troca" : "Mover"}`,
      "1 alteração",
      ...stepDetailsLines({
        step: item.step,
        dependencies: item.step.dependencies,
        dependencyLookup,
        conflictSessionIds,
        conflictLookup,
        currentOrder: index,
      }),
    ];
  }

  const clusterSessionIds = new Set(
    item.steps.flatMap((step) => step.session_ids.map((sessionId) => normalizeId(sessionId))),
  );

  return [
    "",
    `Passo ${index + 1} · Troca`,
    `${item.steps.length} alterações agrupadas`,
    ...item.steps.flatMap((step) => {
      const externalDependencies = step.dependencies.filter(
        (dependency) => !clusterSessionIds.has(normalizeId(String(dependency))),
      );
      return stepDetailsLines({
        step,
        dependencies: externalDependencies,
        dependencyLookup,
        conflictSessionIds,
        conflictLookup,
        currentOrder: index,
      });
    }),
  ];
}

export function buildPlainTextExport(data: ProjectExportPayload): string {
  const modificationPlanItems = buildModificationPlanItems(data.modification_steps);
  const dependencyLookup = buildDependencyLookup(modificationPlanItems);
  const conflictSessionIds = buildConflictSessionIds(data);
  const conflictLookup = buildConflictLookup(data);
  const lines = [
    "Exportação de alterações de horário",
    `Gerado em: ${new Date().toLocaleString("pt-PT")}`,
    "",
    "Aulas Adicionadas e removidas",
    `Adicionadas · ${data.added_removed_sessions.added.length}`,
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

  lines.push("", `Removidas · ${data.added_removed_sessions.removed.length}`);

  if (data.added_removed_sessions.removed.length) {
    lines.push(
      ...data.added_removed_sessions.removed.flatMap((record, index) =>
        textLinesForRecord(record, `Aula removida ${index + 1}`),
      ),
    );
  } else {
    lines.push("- Sem aulas removidas.");
  }

  lines.push("", `Plano de Modificações (${modificationPlanItems.length})`);

  if (!modificationPlanItems.length) {
    lines.push("- Sem modificações.");
  } else {
    lines.push(
      ...modificationPlanItems.flatMap((item, index) =>
        modificationItemLines({
          item,
          index,
          dependencyLookup,
          conflictSessionIds,
          conflictLookup,
        }),
      ),
    );
  }

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
