import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useProject, useProjectExport } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import ExportStatusSection from "@/components/exporter/ExportStatusSection";
import {
  exporterScrollStorageKey,
  exporterSelectedConflictStorageKey,
  parseStoredScrollTop,
  shouldRestoreExporterScroll,
} from "@/utils/exporter/pageState";

export default function ExporterPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const id = projectId ?? "";
  const mainRef = useRef<HTMLElement>(null);
  const restoredScrollProjectRef = useRef<string | null>(null);
  const project = useProject(id);
  const exportResult = useProjectExport(id);
  const scrollStorageKey = exporterScrollStorageKey(id);
  const selectedConflictStorageKey = exporterSelectedConflictStorageKey(id);

  useEffect(() => {
    const hasSelectedConflict = window.sessionStorage.getItem(selectedConflictStorageKey) !== null;
    const parsedScrollTop = parseStoredScrollTop(window.sessionStorage.getItem(scrollStorageKey));
    if (
      !shouldRestoreExporterScroll({
        projectId: id,
        restoredProjectId: restoredScrollProjectRef.current,
        hasSelectedConflict,
        savedScrollTop: parsedScrollTop,
      })
    ) {
      return;
    }

    window.requestAnimationFrame(() => {
      mainRef.current?.scrollTo({ top: parsedScrollTop ?? 0 });
      restoredScrollProjectRef.current = id;
    });
  }, [id, scrollStorageKey, selectedConflictStorageKey, project.data, exportResult.data]);

  function handleMainScroll() {
    const scrollTop = mainRef.current?.scrollTop ?? 0;
    window.sessionStorage.setItem(scrollStorageKey, String(scrollTop));
  }

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>{project.data ? `Exportar ${project.data.name} · AGH` : "Exportar · AGH"}</title>
      <DashboardNavbar projectId={id} isReady={!!project.data?.ingestion_finished_at} />

      <main ref={mainRef} onScroll={handleMainScroll} className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <ExportStatusSection
            data={exportResult.data}
            isError={exportResult.isError}
            isFetching={exportResult.isFetching}
            isLoading={exportResult.isLoading}
            onRecalculate={() => void exportResult.recalculateExportGraph()}
            projectName={project.data?.name}
          />
        </div>
      </main>
    </div>
  );
}
