import { Link } from "react-router-dom";
import { EmptyState } from "@/components/exporter/ExportSection";
import { formatDuration, formatTime, WEEKDAY_LABELS } from "@/utils/exporter/formatters";
import { subjectTitleLabel, uniqueByLabel } from "@/utils/exporter/relations";
import { buildAddedRemovedSessionHref } from "@/utils/exporter/addedRemovedLinks";
import type { ExportSessionRecord, ProjectExportPayload } from "@/types/exporter";

function sessionTitle(session: ExportSessionRecord): string {
  const classes = uniqueByLabel(session.classes ?? [], (classCode) => classCode).join(", ");
  const subjects = uniqueByLabel(session.subjects ?? [], subjectTitleLabel)
    .map((subject) =>
      [subject.acronym ?? subject.name, subject.code ? `(${subject.code})` : ""]
        .filter(Boolean)
        .join(" "),
    )
    .join(", ");

  return [classes, subjects].filter(Boolean).join(" · ") || "Aula";
}

function sessionMeta(session: ExportSessionRecord): string {
  const weekdayKey = session.weekday?.toLowerCase();
  const weekday =
    weekdayKey && weekdayKey in WEEKDAY_LABELS
      ? WEEKDAY_LABELS[weekdayKey as keyof typeof WEEKDAY_LABELS]
      : null;
  const time = typeof session.start_time === "number" ? formatTime(session.start_time) : null;
  const duration = typeof session.duration === "number" ? formatDuration(session.duration) : null;

  return [session.week, weekday, time, duration].filter(Boolean).join(" · ");
}

function resourceSummary(session: ExportSessionRecord): string[] {
  const rooms = session.rooms?.length ? [`Sala ${session.rooms.join(", ")}`] : [];
  const teachers = session.teachers?.length
    ? [`Docente ${session.teachers.map((teacher) => teacher.acronym || teacher.name).join(", ")}`]
    : [];
  const type = session.type ? [`Tipo ${session.type}`] : [];

  return [...rooms, ...teachers, ...type];
}

export default function AddedRemovedSessions({
  data,
  projectId,
}: {
  data: ProjectExportPayload["added_removed_sessions"];
  projectId: string;
}) {
  const groups = [
    {
      label: "Adicionadas",
      rows: data.added,
      change: "added" as const,
      tone: "text-green-700 bg-green-50 border-green-200",
      cardTone: "hover:border-green-400 hover:bg-green-50/70 focus-visible:ring-green-500",
    },
    {
      label: "Removidas",
      rows: data.removed,
      change: "removed" as const,
      tone: "text-red-700 bg-red-50 border-red-200",
      cardTone: "hover:border-red-400 hover:bg-red-50/70 focus-visible:ring-red-500",
    },
  ];

  if (!data.added.length && !data.removed.length) {
    return <EmptyState>Sem aulas adicionadas ou removidas.</EmptyState>;
  }

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
            {group.rows.map((session) => {
              const resources = resourceSummary(session);
              const href = buildAddedRemovedSessionHref(projectId, session, group.change);
              const content = (
                <>
                  <div className="font-semibold">{sessionTitle(session)}</div>
                  <div className="mt-0.5 text-xs font-medium text-[#6b6375]">
                    {sessionMeta(session) || "Sem detalhes de horário"}
                  </div>
                  {!!resources.length && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {resources.map((item) => (
                        <span
                          key={item}
                          className="inline-flex max-w-full items-center rounded border border-[#d8d3cf] bg-white px-1.5 py-0.5 text-xs font-medium text-[#08060d]"
                        >
                          <span className="truncate">{item}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </>
              );

              const cardClass = `block border-b border-[#e5e4e7] px-4 py-3 text-sm text-[#08060d] last:border-0 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset ${
                href ? group.cardTone : "cursor-default"
              }`;

              if (!href) {
                return (
                  <div key={session.id} className={cardClass} title={`ID: ${session.id}`}>
                    {content}
                  </div>
                );
              }

              return (
                <Link key={session.id} to={href} className={cardClass} title={`ID: ${session.id}`}>
                  {content}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
