import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ClassDetail } from "@/types/project/class";

export function useProjectClass(projectId: string, classId: string) {
  return useQuery({
    queryKey: queryKeys.projects.class(projectId, classId),
    queryFn: () => api.getData<ClassDetail>(`/api/projects/${projectId}/classes/${classId}`),
    enabled: !!projectId && !!classId,
  });
}
