import { useParams } from "react-router-dom";
import { useProject, useProjectExport } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import ExportStatusSection from "@/components/exporter/ExportStatusSection";

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
