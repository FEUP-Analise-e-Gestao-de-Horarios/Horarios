import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { DegreeDetail, DegreesListPayload, DegreeStats } from "@/types/dashboard";

export function useProjectDegrees(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.degrees(projectId),
    queryFn: async (): Promise<DegreeStats[]> => {
      const payload = await api.getData<DegreesListPayload>(`/api/projects/${projectId}/degrees/`);
      return payload.degrees;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectDegree(projectId: string, degreeId: string) {
  return useQuery({
    queryKey: queryKeys.projects.degree(projectId, degreeId),
    queryFn: () => api.getData<DegreeDetail>(`/api/projects/${projectId}/degrees/${degreeId}`),
    enabled: !!projectId && !!degreeId,
  });
}
