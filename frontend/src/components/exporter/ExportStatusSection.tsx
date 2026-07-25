import { useState } from "react";
import { AlertTriangle, CalendarClock, Download, RefreshCw, RotateCcw, X } from "lucide-react";
import { useParams } from "react-router-dom";
import type { ProjectExportPayload } from "@/types/exporter";
import ExportResults from "@/components/exporter/ExportResults";
import { EmptyState, ExportSection } from "@/components/exporter/ExportSection";
import { useClearExportChecklist } from "@/api/hooks/useDashboard";
import { downloadPlainTextExport } from "@/utils/exporter/exportPlainText";

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
  const { projectId = "" } = useParams<{ projectId: string }>();
  const [isClearConfirmOpen, setIsClearConfirmOpen] = useState(false);
  const clearChecklist = useClearExportChecklist(projectId);
  const checkedCount = data?.checked_item_keys?.length ?? 0;

  return (
    <>
      <ExportSection
        title={projectName ? `Exportação · ${projectName}` : "Exportação"}
        collapsible={false}
        action={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {data && !isFetching && !isLoading ? (
              <>
                <button
                  type="button"
                  onClick={() => setIsClearConfirmOpen(true)}
                  disabled={checkedCount === 0 || clearChecklist.isPending}
                  className="inline-flex items-center gap-2 rounded border border-[#d8d3cf] bg-white px-3.5 py-2 text-sm font-semibold text-[#08060d] transition-colors hover:border-[#bdb5ae] hover:bg-[#f9f7f4] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RotateCcw size={14} />
                  Limpar marcações
                </button>
                <button
                  type="button"
                  onClick={() => downloadPlainTextExport(data)}
                  className="inline-flex items-center gap-2 rounded border border-[#d8d3cf] bg-white px-3.5 py-2 text-sm font-semibold text-[#08060d] transition-colors hover:border-[#bdb5ae] hover:bg-[#f9f7f4]"
                >
                  <Download size={14} />
                  Exportar texto
                </button>
              </>
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

      {isClearConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-[#d8d3cf] bg-white shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#e5e4e7] px-5 py-4">
              <div>
                <h2 className="text-base font-bold text-[#08060d]">Limpar marcações?</h2>
                <p className="mt-1 text-sm text-[#6b6375]">
                  Esta ação vai desmarcar todos os itens já assinalados no exportador.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsClearConfirmOpen(false)}
                className="rounded-md border border-[#d8d3cf] p-2 text-[#6b6375] transition-colors hover:bg-[#f9f7f4] hover:text-[#08060d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8c2d19]"
                aria-label="Fechar"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex flex-wrap justify-end gap-2 px-5 py-4">
              <button
                type="button"
                onClick={() => setIsClearConfirmOpen(false)}
                className="rounded border border-[#d8d3cf] bg-white px-3.5 py-2 text-sm font-semibold text-[#08060d] transition-colors hover:bg-[#f9f7f4] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8c2d19]"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => {
                  clearChecklist.mutate(undefined, {
                    onSuccess: () => setIsClearConfirmOpen(false),
                  });
                }}
                disabled={clearChecklist.isPending}
                className="rounded bg-[#8c2d19] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#a33520] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
