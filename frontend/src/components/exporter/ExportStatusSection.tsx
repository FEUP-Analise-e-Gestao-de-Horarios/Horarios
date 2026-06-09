import { AlertTriangle, CalendarClock, Download, RefreshCw } from "lucide-react";
import type { ProjectExportPayload } from "@/types/exporter";
import ExportResults from "@/components/exporter/ExportResults";
import { EmptyState, ExportSection } from "@/components/exporter/ExportSection";
import { downloadPlainTextExport } from "@/utils/exportPlainText";

interface ExportStatusSectionProps {
  data?: ProjectExportPayload;
  isError: boolean;
  isFetching: boolean;
  isLoading: boolean;
  onRecalculate: () => void;
  projectName?: string;
}

export default function ExportStatusSection({
  data,
  isError,
  isFetching,
  isLoading,
  onRecalculate,
  projectName,
}: ExportStatusSectionProps) {
  return (
    <ExportSection
      title={projectName ? `Exportação · ${projectName}` : "Exportação"}
      collapsible={false}
      action={
        <div className="flex flex-wrap items-center justify-end gap-2">
          {data && !isFetching && !isLoading ? (
            <button
              type="button"
              onClick={() => downloadPlainTextExport(data)}
              className="inline-flex items-center gap-2 rounded border border-[#d8d3cf] bg-white px-3.5 py-2 text-sm font-semibold text-[#08060d] transition-colors hover:border-[#bdb5ae] hover:bg-[#f9f7f4]"
            >
              <Download size={14} />
              Exportar texto
            </button>
          ) : null}
          <button
            onClick={() => {
              onRecalculate();
            }}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded bg-[#8c2d19] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#a33520] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} />
            Recalcular
          </button>
        </div>
      }
    >
      {isLoading || isFetching ? (
        <div className="flex items-center gap-3 px-5 py-8 text-sm text-[#6b6375]">
          <CalendarClock size={18} className="animate-pulse text-[#8c2d19]" />A calcular
          exportação...
        </div>
      ) : isError ? (
        <div className="flex items-center gap-3 px-5 py-8 text-sm text-red-700">
          <AlertTriangle size={18} />
          Erro ao calcular a exportação.
        </div>
      ) : data ? (
        <div className="p-5">
          <ExportResults data={data} />
        </div>
      ) : (
        <EmptyState>Sem dados de exportação.</EmptyState>
      )}
    </ExportSection>
  );
}
