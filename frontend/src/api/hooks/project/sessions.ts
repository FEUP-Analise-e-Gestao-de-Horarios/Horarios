import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys, type SessionsQueryFilters } from "@/api/queryKeys";
import type { SessionsResponse, WeekBlockResponse } from "@/types/project/sessions";

export function useProjectSessions(projectId: string, filters: SessionsQueryFilters) {
  return useQuery({
    queryKey: queryKeys.projects.sessions(projectId, filters),
    queryFn: async (): Promise<WeekBlockResponse[]> => {
      const params = new URLSearchParams();
      params.set("year_id", filters.yearId);
      for (const id of filters.subjectIds) params.append("subject_ids", id);
      for (const id of filters.classIds) params.append("class_ids", id);
      for (const day of filters.weekdays) params.append("weekdays", day);
      const payload = await api.getData<SessionsResponse>(
        `/api/projects/${projectId}/sessions/?${params.toString()}`,
      );
      return payload.blocks;
    },
    enabled: !!projectId && !!filters.yearId,
  });
}
