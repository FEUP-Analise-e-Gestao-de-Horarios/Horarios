import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useProject, useProjectStats } from "@/api/hooks/project/project";
import { queryKeys } from "@/api/queryKeys";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import ProjectHeader from "@/components/dashboard/ProjectHeader";
import StatsRow from "@/components/dashboard/StatsRow";
import DashboardTabs from "@/components/dashboard/DashboardTabs";

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const id = projectId ?? "";
  const queryClient = useQueryClient();

  const project = useProject(id);

  const processing =
    !!project.data?.ingestion_started_at &&
    !project.data?.ingestion_finished_at &&
    !project.data?.ingestion_failed_at;
  const pollInterval = processing ? 2000 : false;

  const wasProcessing = useRef(false);
  useEffect(() => {
    if (wasProcessing.current && !processing && project.data) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    }
    wasProcessing.current = processing;
  }, [processing, project.data, queryClient]);

  const stats = useProjectStats(id, pollInterval);

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>{project.data ? `${project.data.name} · AGH` : "A carregar… · AGH"}</title>
      <DashboardNavbar projectId={id} isReady={!!project.data?.ingestion_finished_at} />

      <div className="flex-1 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-6 h-full flex flex-col gap-5">
          {project.isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-24 shrink-0 animate-pulse" />
          ) : project.data ? (
            <div className="shrink-0">
              <ProjectHeader project={project.data} />
            </div>
          ) : null}

          {stats.isLoading ? (
            <div className="flex flex-wrap gap-3 shrink-0">
              {Array.from({ length: 7 }).map((_, i) => (
                <div
                  key={i}
                  className="flex-1 min-w-[120px] h-20 bg-white rounded-lg border border-[#e5e4e7] animate-pulse"
                />
              ))}
            </div>
          ) : stats.data ? (
            <div className="shrink-0">
              <StatsRow stats={stats.data} processing={processing} />
            </div>
          ) : null}

          <DashboardTabs projectId={id} pollInterval={pollInterval} processing={processing} />
        </div>
      </div>
    </div>
  );
}
