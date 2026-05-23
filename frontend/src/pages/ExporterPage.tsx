import type { ReactNode } from "react";
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

function formatTime(value: number): string {
  const hours = Math.floor(value / 100);
  const minutes = value % 100;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
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

function isColumnChange(change: ExportFieldModification): change is { old: unknown; new: unknown } {
  return typeof change === "object" && change !== null && "old" in change && "new" in change;
}

function isRelationChange(change: ExportFieldModification): change is {
  added: unknown[];
  removed: unknown[];
} {
  return typeof change === "object" && change !== null && "added" in change && "removed" in change;
}

function relationLabel(item: unknown): string {
  if (typeof item !== "object" || item === null) return formatJsonValue(item);
  const record = item as Record<string, ExportJsonValue>;
  return formatJsonValue(record.room ?? record.teacher ?? record.class ?? record.subject ?? item);
}

function sessionTitle(session: ExportSessionSnapshot): string {
  const subjects = session.subjects.map((subject) => subject.code || subject.name).join(", ");
  const classes = session.classes.join(", ");
  return [subjects, classes].filter(Boolean).join(" · ") || session.id;
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
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#e5e4e7] text-left text-xs font-semibold uppercase tracking-wider text-[#08060d]">
            <th className="px-4 py-2.5">Recurso</th>
            <th className="px-4 py-2.5">Semana</th>
            <th className="px-4 py-2.5">Dia</th>
            <th className="px-4 py-2.5 text-right">Hora</th>
            <th className="px-4 py-2.5 text-right">Duração</th>
            <th className="px-4 py-2.5 text-right">Sessões</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={`${getName(row)}-${row.week}-${row.weekday}-${row.start_time}-${index}`}
              className="border-b border-[#e5e4e7] last:border-0"
            >
              <td className="px-4 py-3 font-medium text-[#08060d]">{getName(row)}</td>
              <td className="px-4 py-3 text-[#6b6375]">{row.week}</td>
              <td className="px-4 py-3 text-[#6b6375]">{WEEKDAY_LABELS[row.weekday]}</td>
              <td className="px-4 py-3 text-right text-[#6b6375]">{formatTime(row.start_time)}</td>
              <td className="px-4 py-3 text-right text-[#6b6375]">
                {formatDuration(row.duration)}
              </td>
              <td className="px-4 py-3 text-right text-[#6b6375]">{row.session_ids.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
    return (
      <div className="grid gap-2 rounded-md border border-[#e5e4e7] bg-[#f9f7f4] p-3 sm:grid-cols-[140px_1fr]">
        <div className="text-xs font-bold uppercase tracking-wider text-[#08060d]">{name}</div>
        <div className="min-w-0 text-sm text-[#6b6375]">
          <span className="line-through">{formatJsonValue(change.old)}</span>
          <span className="mx-2 text-[#08060d]">→</span>
          <span className="font-medium text-[#08060d]">{formatJsonValue(change.new)}</span>
        </div>
      </div>
    );
  }

  if (isRelationChange(change)) {
    return (
      <div className="grid gap-2 rounded-md border border-[#e5e4e7] bg-[#f9f7f4] p-3 sm:grid-cols-[140px_1fr]">
        <div className="text-xs font-bold uppercase tracking-wider text-[#08060d]">{name}</div>
        <div className="space-y-1 text-sm text-[#6b6375]">
          {!!change.added.length && <p>+ {change.added.map(relationLabel).join(", ")}</p>}
          {!!change.removed.length && <p>- {change.removed.map(relationLabel).join(", ")}</p>}
        </div>
      </div>
    );
  }

  return null;
}

function SessionSummary({ session }: { session: ExportSessionSnapshot }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[#6b6375]">
      <span className="font-semibold text-[#08060d]">{sessionTitle(session)}</span>
      <span>{WEEKDAY_LABELS[session.weekday]}</span>
      <span>{formatTime(session.start_time)}</span>
      <span>{formatDuration(session.duration)}</span>
      {!!session.rooms.length && <span>{session.rooms.join(", ")}</span>}
      {!!session.teachers.length && (
        <span>{session.teachers.map((teacher) => teacher.acronym || teacher.name).join(", ")}</span>
      )}
    </div>
  );
}

function ModificationStepCard({ step, index }: { step: ExportModificationStep; index: number }) {
  const entries = Object.entries(step.sessions);
  const Icon = step.type === "exchange" ? Shuffle : ArrowLeftRight;

  return (
    <article className="rounded-lg border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-[#e5e4e7] bg-[#f9f7f4] px-4 py-3">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-[#8c2d19]" />
          <h3 className="text-sm font-bold text-[#08060d]">
            Passo {index + 1} · {step.type === "exchange" ? "Troca" : "Mover"}
          </h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">{entries.length} sessões</span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        {entries.map(([sessionId, item]) => (
          <div key={sessionId} className="p-4">
            <SessionSummary session={item.session} />
            {!!item.dependencies.length && (
              <p className="mt-2 text-xs text-[#6b6375]">
                Dependências: {item.dependencies.map(String).join(", ")}
              </p>
            )}
            <div className="mt-3 grid gap-2">
              {Object.entries(item.modifications).map(([name, change]) =>
                change ? <ModificationChange key={name} name={name} change={change} /> : null,
              )}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function ExportResults({ data }: { data: ProjectExportPayload }) {
  const totalConflicts =
    data.rooms_conflicts.length + data.teacher_conflicts.length + data.classes_conflicts.length;
  const changedSessions = data.modification_steps.reduce(
    (total, step) => total + Object.keys(step.sessions).length,
    0,
  );

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Passos" value={data.modification_steps.length} />
        <StatCard label="Sessões alteradas" value={changedSessions} />
        <StatCard label="Adicionadas" value={data.added_removed_sessions.added.length} />
        <StatCard label="Removidas" value={data.added_removed_sessions.removed.length} />
        <StatCard
          label="Conflitos"
          value={totalConflicts}
          tone={totalConflicts ? "danger" : "neutral"}
        />
      </div>

      <Section title="Conflitos">
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
      </Section>

      <Section title="Sessões">
        <AddedRemovedSessions data={data.added_removed_sessions} />
      </Section>

      <Section title="Plano de Modificações">
        {data.modification_steps.length ? (
          <div className="grid gap-4 p-5">
            {data.modification_steps.map((step, index) => (
              <ModificationStepCard key={index} step={step} index={index} />
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
                onClick={() => void exportResult.refetch()}
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
