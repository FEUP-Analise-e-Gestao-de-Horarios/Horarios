import { useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, ArrowLeftRight, Shuffle } from "lucide-react";
import { EmptyState, ExportSection } from "@/components/exporter/ExportSection";
import type {
  ExportClassConflict,
  ExportConflictBase,
  ExportFieldModification,
  ExportJsonValue,
  ExportModificationStep,
  ExportRoomConflict,
  ExportSessionSnapshot,
  ExportTeacherConflict,
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

function formatConflictWeeks(row: ExportConflictBase): string {
  const weeks = row.weeks?.length ? [...new Set(row.weeks)] : [row.week];
  if (weeks.length === 1) return weeks[0] ?? row.week;
  return `${weeks[0]} a ${weeks[weeks.length - 1]} · ${weeks.length} semanas`;
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

function fieldLabel(name: string): string {
  return FIELD_LABELS[name] ?? name.replaceAll("_", " ");
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

function tooltipAddsInformation(label: string, content?: string): boolean {
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

function StyledTooltip({ content, children }: { content?: string; children: ReactNode }) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);

  if (!content) return children;

  function showTooltip(target: EventTarget | null) {
    if (!(target instanceof HTMLElement)) return;
    const rect = target.getBoundingClientRect();
    setPosition({ x: rect.left + rect.width / 2, y: rect.top });
  }

  const lines = content.split("\n").filter(Boolean);

  return (
    <span
      className="inline-flex max-w-full"
      onMouseEnter={(event) => showTooltip(event.currentTarget)}
      onMouseLeave={() => setPosition(null)}
      onFocus={(event) => showTooltip(event.currentTarget)}
      onBlur={() => setPosition(null)}
    >
      {children}
      {position &&
        createPortal(
          <div
            role="tooltip"
            className="pointer-events-none fixed z-50 max-w-xs -translate-x-1/2 -translate-y-full rounded-md border border-[#2f3037] bg-[#1e2028] px-3 py-2 text-left text-xs leading-5 text-white shadow-[0_10px_30px_rgba(0,0,0,0.25)]"
            style={{ left: position.x, top: position.y - 8 }}
          >
            {lines.map((line, index) => {
              const [label, ...rest] = line.split(": ");
              const value = rest.join(": ");

              return (
                <div key={`${line}-${index}`} className="grid grid-cols-[auto_1fr] gap-x-2">
                  {value ? (
                    <>
                      <span className="font-semibold text-[#f1c9bc]">{label}:</span>
                      <span className="break-words text-white">{value}</span>
                    </>
                  ) : (
                    <span className="col-span-2 break-words text-white">{line}</span>
                  )}
                </div>
              );
            })}
          </div>,
          document.body,
        )}
    </span>
  );
}

function relationRecord(item: unknown): { label: string; title?: string } {
  if (typeof item !== "object" || item === null) {
    const label = cleanLegacyModelLabel(formatJsonValue(item));
    return { label };
  }
  const record = item as Record<string, ExportJsonValue>;
  const label = preferredRecordLabel(record);
  const title = recordDetails(record);
  return { label, title: tooltipAddsInformation(label, title) ? title : undefined };
}

function EntityChip({ item }: { item: unknown }) {
  const relation = relationRecord(item);

  return (
    <StyledTooltip content={relation.title}>
      <span className="inline-flex max-w-full items-center rounded border border-[#d8d3cf] bg-white px-1 py-0 text-xs font-medium text-[#08060d]">
        <span className="truncate">{relation.label}</span>
      </span>
    </StyledTooltip>
  );
}

function uniqueByLabel<T>(items: T[], getLabel: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const label = getLabel(item);
    if (seen.has(label)) return false;
    seen.add(label);
    return true;
  });
}

function AttributeGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="inline-flex min-w-0 flex-wrap items-center gap-0.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-[#08060d]">{label}:</span>
      {children}
    </span>
  );
}

function SummaryLine({ children }: { children: ReactNode }) {
  return <div className="flex min-w-0 flex-wrap items-center gap-1">{children}</div>;
}

function TextValue({ label, value }: { label: string; value: string }) {
  return (
    <AttributeGroup label={label}>
      <span className="text-sm text-[#6b6375]">{value}</span>
    </AttributeGroup>
  );
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

  const uniqueWeeks = Array.from(new Set(weeks));
  return uniqueWeeks.join(", ") || step.session.week;
}

function shouldShowWeekScope(step: ExportModificationStep): boolean {
  if (step.applies_to_all_weeks === false) return true;
  if (step.applies_to_all_weeks === true) return false;

  return new Set(step.weeks).size === 1;
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

function sessionTitle(session: ExportSessionSnapshot): string {
  const subjects = uniqueByLabel(session.subjects, (subject) => relationRecord(subject).label)
    .map((subject) => relationRecord(subject).label)
    .join(", ");
  const classes = uniqueByLabel(session.classes, (classCode) => classCode).join(", ");
  return [subjects, classes].filter(Boolean).join(" · ") || "Sessão";
}

function changeTitle(session: ExportSessionSnapshot): string {
  return `${sessionTitle(session)} · ${WEEKDAY_LABELS[session.weekday]} ${formatTime(
    session.start_time,
  )}`;
}

function normalizeId(value: string): string {
  return value.replaceAll("-", "");
}

function anchorId(sessionId: string): string {
  return `change-${normalizeId(sessionId)}`;
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

interface DependencyTarget {
  anchor: string;
  label: string;
  order: number;
}

type DependencyLookup = Record<string, DependencyTarget>;

type ModificationPlanItem =
  | { kind: "single"; step: ExportModificationStep }
  | { kind: "exchangeCluster"; steps: ExportModificationStep[] };

function buildConflictSessionIds(data: ProjectExportPayload): Set<string> {
  return new Set(
    [...data.rooms_conflicts, ...data.teacher_conflicts, ...data.classes_conflicts].flatMap(
      (conflict) => conflict.session_ids.map((sessionId) => normalizeId(sessionId)),
    ),
  );
}

function modificationPlanItemSteps(item: ModificationPlanItem): ExportModificationStep[] {
  return item.kind === "exchangeCluster" ? item.steps : [item.step];
}

function buildDependencyLookup(items: ModificationPlanItem[]): DependencyLookup {
  const lookup: DependencyLookup = {};

  for (const [itemIndex, item] of items.entries()) {
    const stepNumber = itemIndex + 1;
    for (const step of modificationPlanItemSteps(item)) {
      for (const sessionId of step.session_ids) {
        lookup[normalizeId(sessionId)] = {
          anchor: anchorId(sessionId),
          label: `Passo ${stepNumber}`,
          order: itemIndex,
        };
      }
    }
  }

  return lookup;
}

function buildModificationPlanItems(steps: ExportModificationStep[]): ModificationPlanItem[] {
  const exchangeIndexes = steps
    .map((step, index) => ({ step, index }))
    .filter(({ step }) => step.type === "exchange");
  const exchangeIndexBySessionId = new Map<string, number>();

  for (const { step, index } of exchangeIndexes) {
    for (const sessionId of step.session_ids) {
      exchangeIndexBySessionId.set(normalizeId(sessionId), index);
    }
  }

  const parent = new Map<number, number>();
  for (const { index } of exchangeIndexes) {
    parent.set(index, index);
  }

  function find(index: number): number {
    const current = parent.get(index);
    if (current === undefined || current === index) return index;

    const root = find(current);
    parent.set(index, root);
    return root;
  }

  function union(left: number, right: number) {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) parent.set(rightRoot, leftRoot);
  }

  for (const { step, index } of exchangeIndexes) {
    for (const dependency of step.dependencies) {
      const dependencyIndex = exchangeIndexBySessionId.get(normalizeId(String(dependency)));
      if (dependencyIndex !== undefined) union(index, dependencyIndex);
    }
  }

  const groupsByRoot = new Map<number, number[]>();
  for (const { index } of exchangeIndexes) {
    const root = find(index);
    groupsByRoot.set(root, [...(groupsByRoot.get(root) ?? []), index]);
  }

  const clusteredIndexes = new Set<number>();
  const clusterByFirstIndex = new Map<number, number[]>();
  for (const indexes of groupsByRoot.values()) {
    if (indexes.length < 2) continue;

    const sortedIndexes = indexes.toSorted((left, right) => left - right);
    const firstIndex = sortedIndexes[0];
    if (firstIndex === undefined) continue;

    for (const index of sortedIndexes) clusteredIndexes.add(index);
    clusterByFirstIndex.set(firstIndex, sortedIndexes);
  }

  return steps.flatMap((step, index): ModificationPlanItem[] => {
    const clusterIndexes = clusterByFirstIndex.get(index);
    if (clusterIndexes) {
      const clusterSteps = clusterIndexes
        .map((stepIndex) => steps[stepIndex])
        .filter((clusterStep): clusterStep is ExportModificationStep => clusterStep !== undefined);

      return [{ kind: "exchangeCluster", steps: clusterSteps }];
    }

    if (clusteredIndexes.has(index)) return [];
    return [{ kind: "single", step }];
  });
}

function DependencyLinks({
  dependencies,
  lookup,
  currentOrder,
  onDependencyClick,
  className = "mt-2",
}: {
  dependencies: string[];
  lookup: DependencyLookup;
  currentOrder: number;
  onDependencyClick: (anchor: string) => void;
  className?: string;
}) {
  const flaggedDependencies = dependencies.filter((dependency) => {
    const target = lookup[normalizeId(String(dependency))];
    return target ? target.order > currentOrder : false;
  });

  if (!flaggedDependencies.length) return null;

  return (
    <div className={`inline-flex flex-wrap items-center gap-1 text-xs ${className}`}>
      <span className="font-semibold uppercase tracking-wide text-red-700">Dependências:</span>
      {flaggedDependencies.map((dependency) => {
        const target = lookup[normalizeId(String(dependency))];
        if (!target) {
          return (
            <span
              key={dependency}
              className="rounded border border-red-200 bg-red-50 px-1 py-0.5 text-red-700"
            >
              {shortId(String(dependency))}
            </span>
          );
        }

        return (
          <a
            key={dependency}
            href={`#${target.anchor}`}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onDependencyClick(target.anchor);
            }}
            className="rounded border border-red-200 bg-red-50 px-1 py-0.5 font-medium text-red-700 hover:border-red-400 hover:bg-red-100"
          >
            {target.label}
          </a>
        );
      })}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  const toneClasses =
    tone === "warning"
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : tone === "danger"
        ? "text-red-700 bg-red-50 border-red-200"
        : "text-[#08060d] bg-white border-[#e5e4e7]";

  return (
    <div
      className={`rounded-lg border px-3 py-2 shadow-[0_2px_8px_rgba(0,0,0,0.04)] ${toneClasses}`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider opacity-75">{label}</p>
      <p className="text-xl font-bold leading-tight">{value}</p>
    </div>
  );
}

function ConflictRows<T extends ExportConflictBase>({
  rows,
  getName,
}: {
  rows: T[];
  getName: (row: T) => string;
}) {
  if (!rows.length) return <EmptyState>Sem conflitos.</EmptyState>;

  return (
    <div className="divide-y divide-[#e5e4e7]">
      {rows.map((row, index) => (
        <div
          key={`${getName(row)}-${row.week}-${row.weekday}-${row.start_time}-${index}`}
          className="px-4 py-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="min-w-0 break-words text-sm font-semibold text-[#08060d]">
              {getName(row)}
            </span>
            <span className="rounded border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700">
              {row.session_ids.length} sessões
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#6b6375]">
            <span>{formatConflictWeeks(row)}</span>
            <span>{WEEKDAY_LABELS[row.weekday]}</span>
            <span>{formatTime(row.start_time)}</span>
            <span>{formatDuration(row.duration)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function AddedRemovedSessions({ data }: { data: ProjectExportPayload["added_removed_sessions"] }) {
  const groups = [
    { label: "Adicionadas", rows: data.added, tone: "text-green-700 bg-green-50 border-green-200" },
    { label: "Removidas", rows: data.removed, tone: "text-red-700 bg-red-50 border-red-200" },
  ];

  if (!data.added.length && !data.removed.length)
    return <EmptyState>Sem aulas adicionadas ou removidas.</EmptyState>;

  return (
    <div className="grid gap-4 p-5 md:grid-cols-2">
      {groups.map((group) => (
        <div key={group.label} className="rounded-lg border border-[#e5e4e7] overflow-hidden">
          <div
            className={`border-b px-4 py-2 text-xs font-bold uppercase tracking-wider ${group.tone}`}
          >
            {group.label} · {group.rows.length}
          </div>
          <div className="max-h-72 overflow-auto">
            {group.rows.map((session) => (
              <div
                key={session.id}
                className="border-b border-[#e5e4e7] px-4 py-2.5 text-sm text-[#08060d] last:border-0"
              >
                <code className="text-xs">{session.id}</code>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ModificationChange({
  name,
  change,
  stepType,
}: {
  name: string;
  change: ExportFieldModification;
  stepType?: ExportModificationStep["type"];
}) {
  if (isColumnChange(change)) {
    const oldValue = formatFieldValue(name, change.old);
    const newValue = formatFieldValue(name, change.new);

    return (
      <div className="inline-flex max-w-full flex-wrap items-center gap-1 rounded border border-[#e5e4e7] bg-[#f9f7f4] px-1.5 py-0.5">
        <span className="text-[11px] font-bold uppercase text-[#08060d]">{fieldLabel(name)}</span>
        <span className="min-w-0 text-xs text-[#6b6375]">
          <span className="line-through">{oldValue}</span>
          <span className="mx-1 text-[#08060d]">→</span>
          <span className="font-medium text-[#08060d]">{newValue}</span>
        </span>
      </div>
    );
  }

  if (isRelationChange(change)) {
    const label = fieldLabel(name);
    const clusterRelations = stepType === "exchange" && label === "Turmas";

    function renderItems(items: unknown[]) {
      return items.map((item, index) => <EntityChip key={index} item={item} />);
    }

    return (
      <div className="inline-flex max-w-full flex-wrap items-center gap-1 rounded border border-[#e5e4e7] bg-[#f9f7f4] px-1.5 py-0.5">
        <span className="text-[11px] font-bold uppercase text-[#08060d]">{label}</span>
        <div className="inline-flex flex-wrap items-center gap-1 text-xs text-[#6b6375]">
          {clusterRelations ? (
            <div className="flex flex-wrap items-center gap-1">
              {change.added.length > 0 && (
                <>
                  <span className="text-xs font-bold text-green-700">+</span>
                  {renderItems(change.added)}
                </>
              )}
              {change.added.length > 0 && change.removed.length > 0 && (
                <span className="text-[11px] font-semibold uppercase text-[#08060d]">↔</span>
              )}
              {change.removed.length > 0 && (
                <>
                  <span className="text-xs font-bold text-red-700">-</span>
                  {renderItems(change.removed)}
                </>
              )}
            </div>
          ) : (
            <>
              {!!change.added.length && (
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-xs font-bold text-green-700">+</span>
                  <span className="text-[11px] font-semibold uppercase text-[#08060d]">
                    {relationChangeLabel(label, "added")}:
                  </span>
                  {renderItems(change.added)}
                </div>
              )}
              {!!change.removed.length && (
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-xs font-bold text-red-700">-</span>
                  <span className="text-[11px] font-semibold uppercase text-[#08060d]">
                    {relationChangeLabel(label, "removed")}:
                  </span>
                  {renderItems(change.removed)}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  return null;
}

function SessionAttributes({
  session,
  weekLabel,
}: {
  session: ExportSessionSnapshot;
  weekLabel: string;
}) {
  const subjects = uniqueByLabel(session.subjects, (subject) => relationRecord(subject).label);
  const classes = uniqueByLabel(session.classes, (classCode) => classCode);
  const rooms = uniqueByLabel(session.rooms, (room) => room);
  const teachers = uniqueByLabel(session.teachers, (teacher) => relationRecord(teacher).label);

  return (
    <div className="space-y-1 text-sm text-[#6b6375]">
      <SummaryLine>
        <TextValue label="Duração" value={formatDuration(session.duration)} />
        <TextValue label="Semana" value={weekLabel} />
      </SummaryLine>
      <SummaryLine>
        {!!subjects.length && (
          <AttributeGroup label="UCs">
            {subjects.map((subject) => (
              <EntityChip key={`${subject.code}-${subject.name}`} item={subject} />
            ))}
          </AttributeGroup>
        )}
        {!!classes.length && (
          <AttributeGroup label="Turmas">
            {classes.map((classCode) => (
              <EntityChip key={classCode} item={classCode} />
            ))}
          </AttributeGroup>
        )}
        {!!rooms.length && (
          <AttributeGroup label="Salas">
            {rooms.map((room) => (
              <EntityChip key={room} item={room} />
            ))}
          </AttributeGroup>
        )}
        {!!teachers.length && (
          <AttributeGroup label="Docentes">
            {teachers.map((teacher) => (
              <EntityChip key={`${teacher.number}-${teacher.acronym}`} item={teacher} />
            ))}
          </AttributeGroup>
        )}
      </SummaryLine>
    </div>
  );
}

function ChangeDetails({
  step,
  dependencies,
  dependencyLookup,
  conflictSessionIds,
  highlightedAnchor,
  onDependencyClick,
  getSessionOrder,
}: {
  step: ExportModificationStep;
  dependencies: string[];
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const [isAttributesOpen, setIsAttributesOpen] = useState(false);
  const hasUnsolvedConflict = step.session_ids.some((sessionId) =>
    conflictSessionIds.has(normalizeId(sessionId)),
  );
  const isHighlighted = step.session_ids.some(
    (sessionId) => highlightedAnchor === anchorId(sessionId),
  );

  return (
    <div
      className={`relative scroll-mt-4 overflow-hidden px-2 py-1 transition-colors duration-500 ease-out ${
        hasUnsolvedConflict ? "bg-red-100/90" : isHighlighted ? "bg-amber-50" : "bg-white"
      } ${isHighlighted ? "ring-2 ring-inset ring-amber-400" : ""}`}
    >
      {hasUnsolvedConflict && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 animate-pulse bg-red-300/70"
        />
      )}
      {isHighlighted && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 animate-pulse bg-amber-300/60"
        />
      )}
      <div className="relative z-10">
        {step.session_ids.map((sessionId) => (
          <span key={sessionId} id={anchorId(sessionId)} className="block scroll-mt-4" />
        ))}
        <details
          open={isAttributesOpen}
          onToggle={(event) => setIsAttributesOpen(event.currentTarget.open)}
        >
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-1.5 rounded px-1 py-0.5 marker:hidden hover:bg-white/50">
            <span className="min-w-0 break-words text-sm font-semibold text-[#08060d]">
              {changeTitle(step.session)}
            </span>
            {shouldShowWeekScope(step) && (
              <span className="inline-flex items-center rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs font-semibold text-amber-700">
                Semanas {formatWeekLabel(step)}
              </span>
            )}
            <DependencyLinks
              dependencies={dependencies}
              lookup={dependencyLookup}
              currentOrder={Math.min(...step.session_ids.map(getSessionOrder))}
              onDependencyClick={onDependencyClick}
              className="mt-0"
            />
            <span className="ml-auto inline-flex flex-wrap items-center justify-end gap-1.5 whitespace-nowrap">
              {hasUnsolvedConflict && (
                <span className="inline-flex items-center gap-1 rounded border border-red-300 bg-red-50 px-1.5 py-0.5 text-xs font-semibold text-red-800">
                  <AlertTriangle size={12} />
                  Esta alteração causa um conflito por resolver
                </span>
              )}
              <span className="text-xs font-semibold text-[#8c2d19]">
                {isAttributesOpen ? "Esconder atributos" : "Ver atributos"}
              </span>
            </span>
          </summary>
          <div className="mt-1 px-1 pb-0.5">
            <SessionAttributes session={step.session} weekLabel={formatWeekLabel(step)} />
          </div>
        </details>
        <div className="mt-1 flex flex-wrap gap-1">
          {Object.entries(step.modifications).map(([name, change]) =>
            change ? (
              <ModificationChange key={name} name={name} change={change} stepType={step.type} />
            ) : null,
          )}
        </div>
      </div>
    </div>
  );
}

function ModificationStepCard({
  step,
  index,
  dependencyLookup,
  conflictSessionIds,
  highlightedAnchor,
  onDependencyClick,
  getSessionOrder,
}: {
  step: ExportModificationStep;
  index: number;
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const Icon = step.type === "exchange" ? Shuffle : ArrowLeftRight;

  return (
    <article className="rounded-md border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e4e7] bg-[#f9f7f4] px-3 py-1">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className="text-[#8c2d19]" />
          <h3 className="text-sm font-bold text-[#08060d]">
            Passo {index + 1} · {step.type === "exchange" ? "Troca" : "Mover"}
          </h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">1 alteração</span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        <ChangeDetails
          step={step}
          dependencies={step.dependencies}
          dependencyLookup={dependencyLookup}
          conflictSessionIds={conflictSessionIds}
          highlightedAnchor={highlightedAnchor}
          onDependencyClick={onDependencyClick}
          getSessionOrder={getSessionOrder}
        />
      </div>
    </article>
  );
}

function ExchangeClusterCard({
  steps,
  index,
  dependencyLookup,
  conflictSessionIds,
  highlightedAnchor,
  onDependencyClick,
  getSessionOrder,
}: {
  steps: ExportModificationStep[];
  index: number;
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const clusterSessionIds = new Set(
    steps.flatMap((step) => step.session_ids.map((sessionId) => normalizeId(sessionId))),
  );

  return (
    <article className="rounded-md border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e4e7] bg-[#f9f7f4] px-3 py-1">
        <div className="flex items-center gap-1.5">
          <Shuffle size={14} className="text-[#8c2d19]" />
          <h3 className="text-sm font-bold text-[#08060d]">Passo {index + 1} · Troca</h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">
          {steps.length} alterações agrupadas
        </span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        {steps.map((step) => {
          const externalDependencies = step.dependencies.filter(
            (dependency) => !clusterSessionIds.has(normalizeId(String(dependency))),
          );

          return (
            <ChangeDetails
              key={step.session_ids.join("-")}
              step={step}
              dependencies={externalDependencies}
              dependencyLookup={dependencyLookup}
              conflictSessionIds={conflictSessionIds}
              highlightedAnchor={highlightedAnchor}
              onDependencyClick={onDependencyClick}
              getSessionOrder={getSessionOrder}
            />
          );
        })}
      </div>
    </article>
  );
}

export default function ExportResults({ data }: { data: ProjectExportPayload }) {
  const [highlightedAnchor, setHighlightedAnchor] = useState<string | null>(null);
  const highlightTimeoutRef = useRef<number | null>(null);
  const modificationPlanItems = useMemo(
    () => buildModificationPlanItems(data.modification_steps),
    [data.modification_steps],
  );
  const dependencyLookup = useMemo(
    () => buildDependencyLookup(modificationPlanItems),
    [modificationPlanItems],
  );
  const conflictSessionIds = useMemo(() => buildConflictSessionIds(data), [data]);
  function getSessionOrder(sessionId: string) {
    return dependencyLookup[normalizeId(sessionId)]?.order ?? Number.MAX_SAFE_INTEGER;
  }

  function handleDependencyClick(anchor: string) {
    setHighlightedAnchor(anchor);
    document.getElementById(anchor)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    if (highlightTimeoutRef.current !== null) {
      window.clearTimeout(highlightTimeoutRef.current);
    }

    highlightTimeoutRef.current = window.setTimeout(() => {
      setHighlightedAnchor(null);
      highlightTimeoutRef.current = null;
    }, 2400);
  }

  const totalConflicts =
    data.rooms_conflicts.length + data.teacher_conflicts.length + data.classes_conflicts.length;
  const changedBlocks = data.modification_steps.length;

  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Passos" value={data.modification_steps.length} />
        <StatCard label="Alterações" value={changedBlocks} />
        <StatCard label="Adicionadas" value={data.added_removed_sessions.added.length} />
        <StatCard label="Removidas" value={data.added_removed_sessions.removed.length} />
        <StatCard
          label="Conflitos"
          value={totalConflicts}
          tone={totalConflicts ? "danger" : "neutral"}
        />
      </div>

      <ExportSection
        title="Conflitos"
        action={<span className="text-xs text-[#6b6375]">{totalConflicts}</span>}
      >
        <div className="grid gap-5 p-5 xl:grid-cols-3">
          <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
            <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
              Salas · {data.rooms_conflicts.length}
            </div>
            <ConflictRows<ExportRoomConflict>
              rows={data.rooms_conflicts}
              getName={(row) => row.room_name}
            />
          </div>
          <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
            <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
              Docentes · {data.teacher_conflicts.length}
            </div>
            <ConflictRows<ExportTeacherConflict>
              rows={data.teacher_conflicts}
              getName={(row) => `${row.teacher_acronym} · ${row.teacher_name}`}
            />
          </div>
          <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
            <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
              Turmas · {data.classes_conflicts.length}
            </div>
            <ConflictRows<ExportClassConflict>
              rows={data.classes_conflicts}
              getName={(row) => row.class_code}
            />
          </div>
        </div>
      </ExportSection>

      <ExportSection title="Aulas Adicionadas e removidas">
        <AddedRemovedSessions data={data.added_removed_sessions} />
      </ExportSection>

      <ExportSection title="Plano de Modificações" defaultOpen>
        {modificationPlanItems.length ? (
          <div className="grid gap-2 p-3">
            {modificationPlanItems.map((item, index) =>
              item.kind === "exchangeCluster" ? (
                <ExchangeClusterCard
                  key={item.steps.flatMap((step) => step.session_ids).join("-")}
                  steps={item.steps}
                  index={index}
                  dependencyLookup={dependencyLookup}
                  conflictSessionIds={conflictSessionIds}
                  highlightedAnchor={highlightedAnchor}
                  onDependencyClick={handleDependencyClick}
                  getSessionOrder={getSessionOrder}
                />
              ) : (
                <ModificationStepCard
                  key={item.step.session_ids.join("-")}
                  step={item.step}
                  index={index}
                  dependencyLookup={dependencyLookup}
                  conflictSessionIds={conflictSessionIds}
                  highlightedAnchor={highlightedAnchor}
                  onDependencyClick={handleDependencyClick}
                  getSessionOrder={getSessionOrder}
                />
              ),
            )}
          </div>
        ) : (
          <EmptyState>Sem modificações.</EmptyState>
        )}
      </ExportSection>
    </div>
  );
}
