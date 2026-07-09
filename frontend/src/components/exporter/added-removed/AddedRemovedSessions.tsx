import { Link } from "react-router-dom";
import { EmptyState } from "@/components/exporter/ExportSection";
import { EntityChip } from "@/components/exporter/shared/EntityChip";
import { formatDuration, formatTime, WEEKDAY_LABELS } from "@/utils/exporter/formatters";
import { subjectTitleLabel, uniqueByLabel } from "@/utils/exporter/relations";
import { buildAddedRemovedSessionHref } from "@/utils/exporter/addedRemovedLinks";
import type { ExportSessionRecord, ProjectExportPayload } from "@/types/exporter";

interface ResourceGroup {
  label: string;
  items: unknown[];
}

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

function teacherDetailFallbacks(session: ExportSessionRecord) {
  return (
    session.teachers?.map((teacher) => ({
      teacher_number: teacher.number,
      teacher_acronym: teacher.acronym,
      teacher_name: teacher.name,
    })) ?? []
  );
}

function resourceGroups(session: ExportSessionRecord): ResourceGroup[] {
  return [
    {
      label: "Salas",
      items: session.room_details?.length ? session.room_details : (session.rooms ?? []),
    },
    {
      label: "Docentes",
      items: session.teacher_details?.length
        ? session.teacher_details
        : teacherDetailFallbacks(session),
    },
    {
      label: "Tipo",
      items: session.type ? [session.type] : [],
    },
  ].filter((group) => group.items.length > 0);
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
              const resources = resourceGroups(session);
              const href = buildAddedRemovedSessionHref(projectId, session, group.change);
              const content = (
                <>
                  <div className="font-semibold">{sessionTitle(session)}</div>
                  <div className="mt-0.5 text-xs font-medium text-[#6b6375]">
                    {sessionMeta(session) || "Sem detalhes de horário"}
                  </div>
                  {resources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1">
                      {resources.map((resource) => (
                        <div
                          key={resource.label}
                          className="flex min-w-0 flex-wrap items-center gap-1"
                        >
                          <span className="text-[11px] font-bold uppercase text-[#6b6375]">
                            {resource.label}
                          </span>
                          {resource.items.map((item, index) => (
                            <EntityChip key={index} item={item} />
                          ))}
                        </div>
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
                  <div key={session.id} className={cardClass}>
                    {content}
                  </div>
                );
              }

              return (
                <Link key={session.id} to={href} className={cardClass}>
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
