import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Project } from "@/types/project";
import type { ProjectStats } from "@/types/dashboard";

const POLL_INTERVAL = 2000;

function isProcessing(project: Project): boolean {
  return (
    !!project.ingestion_started_at && !project.ingestion_finished_at && !project.ingestion_failed_at
  );
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: () => api.getData<Project>(`/api/projects/${projectId}`),
    enabled: !!projectId,
    refetchInterval: (query) =>
      query.state.data && !isProcessing(query.state.data) ? false : POLL_INTERVAL,
  });
}

export function useProjectStats(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.stats(projectId),
    queryFn: () => api.getData<ProjectStats>(`/api/projects/${projectId}/stats`),
    enabled: !!projectId,
    refetchInterval,
  });
}
