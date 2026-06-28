import type { ReactNode } from "react";
import type { ExportSessionSnapshot } from "@/types/exporter";
import { EntityChip } from "@/components/exporter/shared/EntityChip";
import { formatDuration } from "@/utils/exporter/formatters";
import { relationRecord, uniqueByLabel } from "@/utils/exporter/relations";

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

export default function SessionAttributes({
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
