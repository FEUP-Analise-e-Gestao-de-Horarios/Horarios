import { useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, ArrowLeftRight, CalendarClock, RefreshCw, Shuffle } from "lucide-react";
import { useParams } from "react-router-dom";
import { useProject, useProjectExport } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import ProjectHeader from "@/components/dashboard/ProjectHeader";
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
import type { Weekday } from "@/types/dashboard";

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
      <span className="inline-flex max-w-full items-center rounded border border-[#d8d3cf] bg-white px-2 py-0.5 text-xs font-medium text-[#08060d]">
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
    <span className="inline-flex min-w-0 flex-wrap items-center gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-[#08060d]">{label}:</span>
      {children}
    </span>
  );
}

function SummaryLine({ children }: { children: ReactNode }) {
  return <div className="flex min-w-0 flex-wrap items-center gap-1.5">{children}</div>;
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

function buildDependencyLookup(steps: ExportModificationStep[]): DependencyLookup {
  const lookup: DependencyLookup = {};
  let order = 0;

  for (const step of steps) {
    for (const sessionId of step.session_ids) {
      lookup[normalizeId(sessionId)] = {
        anchor: anchorId(sessionId),
        label: `${sessionTitle(step.session)} · ${WEEKDAY_LABELS[step.session.weekday]} ${formatTime(step.session.start_time)}`,
        order,
      };
      order += 1;
    }
  }

  return lookup;
}

function DependencyLinks({
  dependencies,
  lookup,
  currentOrder,
  onDependencyClick,
}: {
  dependencies: string[];
  lookup: DependencyLookup;
  currentOrder: number;
  onDependencyClick: (anchor: string) => void;
}) {
  const flaggedDependencies = dependencies.filter((dependency) => {
    const target = lookup[normalizeId(String(dependency))];
    return target ? target.order > currentOrder : false;
  });

  if (!flaggedDependencies.length) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
      <span className="font-semibold uppercase tracking-wide text-[#08060d]">Dependências:</span>
      {flaggedDependencies.map((dependency) => {
        const target = lookup[normalizeId(String(dependency))];
        if (!target) {
          return (
            <span
              key={dependency}
              className="rounded border border-[#e5e4e7] bg-[#f9f7f4] px-2 py-0.5 text-[#6b6375]"
            >
              {shortId(String(dependency))}
            </span>
          );
        }

        return (
          <a
            key={dependency}
            href={`#${target.anchor}`}
            onClick={() => onDependencyClick(target.anchor)}
            className="rounded border border-[#d8d3cf] bg-white px-2 py-0.5 font-medium text-[#8c2d19] hover:border-[#8c2d19] hover:bg-[#fff7f4]"
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
    <div className={`rounded-lg border p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] ${toneClasses}`}>
      <p className="text-xs font-semibold uppercase tracking-wider opacity-75">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}

function EmptyState({ children }: { children: string }) {
  return <div className="py-8 text-center text-sm text-[#6b6375]">{children}</div>;
}

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-[#e5e4e7] px-5 py-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-[#08060d]">{title}</h2>
        {action}
      </div>
      {children}
    </section>
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
            <span>{row.week}</span>
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
    return <EmptyState>Sem sessões adicionadas ou removidas.</EmptyState>;

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

function ModificationChange({ name, change }: { name: string; change: ExportFieldModification }) {
  if (isColumnChange(change)) {
    const oldValue = formatFieldValue(name, change.old);
    const newValue = formatFieldValue(name, change.new);

    return (
      <div className="grid gap-2 rounded-md border border-[#e5e4e7] bg-[#f9f7f4] p-3 sm:grid-cols-[140px_1fr]">
        <div className="text-xs font-bold uppercase tracking-wider text-[#08060d]">
          {fieldLabel(name)}
        </div>
        <div className="min-w-0 text-sm text-[#6b6375]">
          <span className="line-through">{oldValue}</span>
          <span className="mx-2 text-[#08060d]">→</span>
          <span className="font-medium text-[#08060d]">{newValue}</span>
        </div>
      </div>
    );
  }

  if (isRelationChange(change)) {
    const label = fieldLabel(name);
    return (
      <div className="grid gap-2 rounded-md border border-[#e5e4e7] bg-[#f9f7f4] p-3 sm:grid-cols-[140px_1fr]">
        <div className="text-xs font-bold uppercase tracking-wider text-[#08060d]">{label}</div>
        <div className="space-y-2 text-sm text-[#6b6375]">
          {!!change.added.length && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-bold text-green-700">+</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-[#08060d]">
                {relationChangeLabel(label, "added")}:
              </span>
              {change.added.map((item, index) => (
                <EntityChip key={index} item={item} />
              ))}
            </div>
          )}
          {!!change.removed.length && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-bold text-red-700">-</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-[#08060d]">
                {relationChangeLabel(label, "removed")}:
              </span>
              {change.removed.map((item, index) => (
                <EntityChip key={index} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}

function SessionSummary({
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
    <div className="space-y-1.5 text-sm text-[#6b6375]">
      <SummaryLine>
        <span className="font-semibold text-[#08060d]">{sessionTitle(session)}</span>
      </SummaryLine>
      <SummaryLine>
        <TextValue label="Dia" value={WEEKDAY_LABELS[session.weekday]} />
        <TextValue label="Hora" value={formatTime(session.start_time)} />
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

function ModificationStepCard({
  step,
  index,
  dependencyLookup,
  highlightedAnchor,
  onDependencyClick,
  getSessionOrder,
}: {
  step: ExportModificationStep;
  index: number;
  dependencyLookup: DependencyLookup;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const Icon = step.type === "exchange" ? Shuffle : ArrowLeftRight;

  return (
    <article className="rounded-lg border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-[#e5e4e7] bg-[#f9f7f4] px-4 py-3">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-[#8c2d19]" />
          <h3 className="text-md font-bold text-[#08060d]">
            Passo {index + 1} · {step.type === "exchange" ? "Troca" : "Mover"}
          </h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">1 alteração</span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        <div
          className={`scroll-mt-4 p-4 transition-colors duration-300 ${
            step.session_ids.some((sessionId) => highlightedAnchor === anchorId(sessionId))
              ? "bg-amber-50 ring-2 ring-inset ring-amber-300"
              : "bg-white"
          }`}
        >
          {step.session_ids.map((sessionId) => (
            <span key={sessionId} id={anchorId(sessionId)} className="block scroll-mt-4" />
          ))}
          <SessionSummary session={step.session} weekLabel={formatWeekLabel(step)} />
          <DependencyLinks
            dependencies={step.dependencies}
            lookup={dependencyLookup}
            currentOrder={Math.min(...step.session_ids.map(getSessionOrder))}
            onDependencyClick={onDependencyClick}
          />
          <div className="mt-3 grid gap-2">
            {Object.entries(step.modifications).map(([name, change]) =>
              change ? <ModificationChange key={name} name={name} change={change} /> : null,
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

function ExportResults({ data }: { data: ProjectExportPayload }) {
  const [highlightedAnchor, setHighlightedAnchor] = useState<string | null>(null);
  const highlightTimeoutRef = useRef<number | null>(null);
  const dependencyLookup = useMemo(
    () => buildDependencyLookup(data.modification_steps),
    [data.modification_steps],
  );
  function getSessionOrder(sessionId: string) {
    return dependencyLookup[normalizeId(sessionId)]?.order ?? Number.MAX_SAFE_INTEGER;
  }

  function handleDependencyClick(anchor: string) {
    setHighlightedAnchor(anchor);

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
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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

      <details className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
        <summary className="flex cursor-pointer items-center justify-between gap-4 px-5 py-3 text-sm font-bold uppercase tracking-wider text-[#08060d]">
          <span>Conflitos</span>
          <span className="text-xs text-[#6b6375]">{totalConflicts}</span>
        </summary>
        <div className="grid gap-5 border-t border-[#e5e4e7] p-5 xl:grid-cols-3">
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
      </details>

      <Section title="Sessões">
        <AddedRemovedSessions data={data.added_removed_sessions} />
      </Section>

      <Section title="Plano de Modificações">
        {data.modification_steps.length ? (
          <div className="grid gap-4 p-5">
            {data.modification_steps.map((step, index) => (
              <ModificationStepCard
                key={index}
                step={step}
                index={index}
                dependencyLookup={dependencyLookup}
                highlightedAnchor={highlightedAnchor}
                onDependencyClick={handleDependencyClick}
                getSessionOrder={getSessionOrder}
              />
            ))}
          </div>
        ) : (
          <EmptyState>Sem modificações.</EmptyState>
        )}
      </Section>
    </div>
  );
}

export default function ExporterPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const id = projectId ?? "";
  const project = useProject(id);
  const exportResult = useProjectExport(id);

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>{project.data ? `Exportar ${project.data.name} · AGH` : "Exportar · AGH"}</title>
      <DashboardNavbar projectId={id} isReady={!!project.data?.ingestion_finished_at} />

      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 space-y-5">
          {project.isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-24 animate-pulse" />
          ) : project.data ? (
            <ProjectHeader project={project.data} />
          ) : null}

          <Section
            title="Exportação"
            action={
              <button
                onClick={() => void exportResult.recalculateExportGraph()}
                disabled={exportResult.isFetching}
                className="inline-flex items-center gap-2 rounded bg-[#8c2d19] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#a33520] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw size={14} className={exportResult.isFetching ? "animate-spin" : ""} />
                Recalcular
              </button>
            }
          >
            {exportResult.isLoading || exportResult.isFetching ? (
              <div className="flex items-center gap-3 px-5 py-8 text-sm text-[#6b6375]">
                <CalendarClock size={18} className="animate-pulse text-[#8c2d19]" />A calcular
                exportação...
              </div>
            ) : exportResult.isError ? (
              <div className="flex items-center gap-3 px-5 py-8 text-sm text-red-700">
                <AlertTriangle size={18} />
                Erro ao calcular a exportação.
              </div>
            ) : exportResult.data ? (
              <div className="p-5">
                <ExportResults data={exportResult.data} />
              </div>
            ) : (
              <EmptyState>Sem dados de exportação.</EmptyState>
            )}
          </Section>
        </div>
      </main>
    </div>
  );
}
