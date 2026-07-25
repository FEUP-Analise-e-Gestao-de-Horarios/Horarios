import WeekGrid from "@/components/dashboard/WeekGrid";
import type {
  DashboardSessionHighlightTone,
  ExportSessionPreview,
} from "@/utils/exporter/dashboardNavigation";

interface ExporterSessionPreviewFallbackProps {
  preview: ExportSessionPreview;
  tone: DashboardSessionHighlightTone;
}

export default function ExporterSessionPreviewFallback({
  preview,
  tone,
}: ExporterSessionPreviewFallbackProps) {
  const title =
    tone === "added" ? "Aula adicionada" : tone === "removed" ? "Aula removida" : "Aula";

  return (
    <>
      <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] px-6 py-4">
        <h1 className="text-2xl font-bold text-[#08060d]">{title}</h1>
        <div className="mt-1 text-sm text-[#6b6375]">{preview.week}</div>
      </div>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[#08060d]">Horário</h2>
      </div>

      <div className="flex-1 min-h-0">
        <WeekGrid
          events={[preview]}
          highlightedEventIds={new Set([preview.id])}
          highlightedEventTone={tone}
          emptyMessage="Sem aulas para apresentar."
        />
      </div>
    </>
  );
}
