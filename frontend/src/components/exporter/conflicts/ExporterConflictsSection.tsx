import type {
  ExportClassConflict,
  ExportRoomConflict,
  ExportTeacherConflict,
  ProjectExportPayload,
} from "@/types/exporter";
import { ExportSection } from "@/components/exporter/ExportSection";
import ConflictRows from "@/components/exporter/conflicts/ConflictRows";
import { conflictCardAnchorId, teacherConflictName } from "@/utils/exporter/conflicts";
import {
  buildClassConflictHref,
  buildRoomConflictHref,
  buildTeacherConflictHref,
} from "@/utils/exporter/conflictLinks";

export default function ExporterConflictsSection({
  data,
  projectId,
  totalConflicts,
  highlightedAnchor,
  isOpen,
  onOpenChange,
  onCardClick,
}: {
  data: ProjectExportPayload;
  projectId: string;
  totalConflicts: number;
  highlightedAnchor: string | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onCardClick: (anchorId: string) => void;
}) {
  return (
    <ExportSection
      title="Conflitos"
      action={<span className="text-xs text-[#6b6375]">{totalConflicts}</span>}
      open={isOpen}
      onOpenChange={onOpenChange}
    >
      <div className="grid gap-5 p-5 xl:grid-cols-3">
        <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
          <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
            Salas · {data.rooms_conflicts.length}
          </div>
          <ConflictRows<ExportRoomConflict>
            rows={data.rooms_conflicts}
            getName={(row) => row.room_name}
            getAnchorId={(row, index) => conflictCardAnchorId("room", row, index)}
            highlightedAnchor={highlightedAnchor}
            getHref={(row) => buildRoomConflictHref(projectId, row)}
            onCardClick={onCardClick}
          />
        </div>
        <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
          <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
            Docentes · {data.teacher_conflicts.length}
          </div>
          <ConflictRows<ExportTeacherConflict>
            rows={data.teacher_conflicts}
            getName={teacherConflictName}
            getAnchorId={(row, index) => conflictCardAnchorId("teacher", row, index)}
            highlightedAnchor={highlightedAnchor}
            getHref={(row) => buildTeacherConflictHref(projectId, row)}
            onCardClick={onCardClick}
          />
        </div>
        <div className="rounded-lg border border-[#e5e4e7] overflow-hidden">
          <div className="border-b border-[#e5e4e7] px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#08060d]">
            Turmas · {data.classes_conflicts.length}
          </div>
          <ConflictRows<ExportClassConflict>
            rows={data.classes_conflicts}
            getName={(row) => row.class_code}
            getAnchorId={(row, index) => conflictCardAnchorId("class", row, index)}
            highlightedAnchor={highlightedAnchor}
            getHref={(row) => buildClassConflictHref(projectId, row)}
            onCardClick={onCardClick}
          />
        </div>
      </div>
    </ExportSection>
  );
}
