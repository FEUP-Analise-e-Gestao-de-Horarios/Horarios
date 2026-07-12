import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useProjectExport } from "@/api/hooks/useDashboard";
import { useProjectAccess } from "@/api/hooks/project/access";
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
  const { project, isPending: isProjectPending, isError: isProjectError } = useProjectAccess(id);
  const isReady = !!project?.ingestion_finished_at;
  // Hold the export POST until the import is known to have finished: without a
  // project there is nothing to export, and useProjectAccess is already
  // redirecting away.
  const exportResult = useProjectExport(id, { enabled: isReady });
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
  }, [id, scrollStorageKey, selectedConflictStorageKey, project, exportResult.data]);

  function handleMainScroll() {
    const scrollTop = mainRef.current?.scrollTop ?? 0;
    window.sessionStorage.setItem(scrollStorageKey, String(scrollTop));
  }

  if (isProjectError) {
    return (
      <div className="h-screen bg-[#f0eeeb] flex items-center justify-center text-center text-gray-500 text-lg">
        Não foi possível carregar o projeto.
      </div>
    );
  }

  // Covers the not-yet-imported project too: useProjectAccess is redirecting to
  // the dashboard, so hold the placeholder rather than flashing an empty page.
  if (isProjectPending || !project?.ingestion_finished_at) {
    return (
      <div className="h-screen bg-[#f0eeeb] flex items-center justify-center text-center text-gray-500 text-lg">
        A carregar…
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>{`Exportar ${project.name} · AGH`}</title>
      <DashboardNavbar projectId={id} isReady />

      <main ref={mainRef} onScroll={handleMainScroll} className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <ExportStatusSection
            data={exportResult.data}
            isError={exportResult.isError}
            isFetching={exportResult.isFetching}
            isLoading={exportResult.isLoading}
            onRecalculate={() => void exportResult.recalculateExportGraph()}
            projectName={project.name}
          />
        </div>
      </main>
    </div>
  );
}
