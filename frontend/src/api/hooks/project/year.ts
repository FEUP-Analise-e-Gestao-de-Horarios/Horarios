import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ConflictRecord } from "@/types/project/conflicts";
import type { YearDetail } from "@/types/project/year";

export function useProjectYear(projectId: string, yearId: string) {
  return useQuery({
    queryKey: queryKeys.projects.year(projectId, yearId),
    queryFn: () => api.getData<YearDetail>(`/api/projects/${projectId}/years/${yearId}`),
    enabled: !!projectId && !!yearId,
  });
}

export function useProjectYearConflicts(projectId: string, yearId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "years", yearId, "conflicts"] as const,
    queryFn: (): ConflictRecord[] => [],
    enabled: false,
    initialData: [] as ConflictRecord[],
  });
}
