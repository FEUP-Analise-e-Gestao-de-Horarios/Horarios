import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { SubjectDetail } from "@/types/project/subject";

export function useProjectSubject(projectId: string, subjectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.subject(projectId, subjectId),
    queryFn: () => api.getData<SubjectDetail>(`/api/projects/${projectId}/subjects/${subjectId}`),
    enabled: !!projectId && !!subjectId,
  });
}
